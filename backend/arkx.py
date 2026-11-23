"""Intercâmbio manual `ARKX v2` com autorização e publicação direta."""
import base64
import hashlib
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import cbor2
import zstandard
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from backend.protocol import artifact_hash, validate_authorization_v2

MAGIC = b"ARKX"
VERSION = 2
MAX_FILE = 128 * 1024 * 1024

class ArkxError(RuntimeError): pass
def _time(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def _unsigned(header): return cbor2.dumps({k:v for k,v in header.items() if k!='assinatura_exportador'},canonical=True)


def _latest_authorization(connection, network_id: str) -> dict:
    """Obtém o último estado conhecido, inclusive a âncora de uma cópia nova."""
    row = connection.execute(
        "SELECT state_artifact FROM authorization_states WHERE network_id=? ORDER BY sequence_number DESC LIMIT 1",
        (network_id,),
    ).fetchone()
    if row is None:
        row = connection.execute(
            "SELECT state_artifact FROM authorization_anchors WHERE network_id=?",
            (network_id,),
        ).fetchone()
    if row is None:
        raise ArkxError("Estado de autorização indisponível.")
    try:
        state = cbor2.loads(row[0])
        validate_authorization_v2(state)
        return state
    except Exception as error:
        raise ArkxError("Estado de autorização indisponível.") from error


def _local_authorizations(connection, network_id: str) -> dict[int, dict]:
    """Retorna os estados públicos conhecidos, inclusive a âncora local."""
    states: dict[int, dict] = {}
    rows = connection.execute(
        "SELECT sequence_number, state_artifact FROM authorization_anchors WHERE network_id=? "
        "UNION ALL SELECT sequence_number, state_artifact FROM authorization_states WHERE network_id=?",
        (network_id, network_id),
    ).fetchall()
    try:
        for sequence, encoded in rows:
            state = cbor2.loads(encoded)
            validate_authorization_v2(state)
            if state["sequencia"] != sequence or (sequence in states and artifact_hash(states[sequence]) != artifact_hash(state)):
                raise ValueError()
            states[sequence] = state
    except Exception as error:
        raise ArkxError("Estado de autorização indisponível.") from error
    if not states:
        raise ArkxError("Estado de autorização indisponível.")
    return states


def _ordered_authorization_chain(available_states: list[dict]) -> list[dict]:
    """Ordena estados públicos recebidos sem aceitar duas versões na mesma sequência."""
    chain_by_sequence = {}
    try:
        for item in available_states:
            validate_authorization_v2(item)
            sequence = item['sequencia']
            if sequence in chain_by_sequence and artifact_hash(chain_by_sequence[sequence]) != artifact_hash(item):
                raise ValueError()
            chain_by_sequence[sequence] = item
        return [chain_by_sequence[sequence] for sequence in sorted(chain_by_sequence)]
    except Exception as error:
        raise ArkxError('Estado de autorização indisponível.') from error


def build_export(connection, identity, mode: str = 'COMPLETA', since: str | None = None, unexported_only: bool = False) -> bytes:
    """Monta exportação com cadeia de autorização e publicações diretas."""
    if mode not in {'RESUMIDA','COMPLETA'}: raise ArkxError('Modalidade de exportação inválida.')
    public=identity['public_identity']
    state = _latest_authorization(connection, public['network_id']); recipients=state['membros']
    if not any(member['status'] == 'ATIVO' for member in recipients): raise ArkxError('Não há destinatários ativos.')
    query="""SELECT p.content_hash,p.author_member_id,p.sequence_number,p.content_type,p.article_id,p.title,p.body,p.previous_publication_hash,p.signature,p.header_signature,p.created_at
        FROM publications p WHERE p.publication_status='PUBLICADO'"""
    params=[]
    if since: query += " AND p.created_at >= ?"; params.append(since)
    if unexported_only: query += " AND p.content_hash NOT IN (SELECT content_hash FROM export_items)"
    rows=connection.execute(query, params).fetchall()
    items=[]
    for row in rows:
        record={'hash':row[0],'autor_id':row[1],'sequencia':row[2],'tipo':row[3],'artigo_id':row[4],'titulo':row[5],'anterior_hash':row[7],'criado_em':row[10],'assinatura':row[8],'assinatura_cabecalho':row[9]}
        if mode=='COMPLETA': record['corpo']=row[6]
        items.append(record)
    export_id=str(uuid4()); key=os.urandom(32); nonce=os.urandom(12)
    anchor_row = connection.execute(
        "SELECT state_artifact FROM authorization_anchors WHERE network_id=?", (public['network_id'],)
    ).fetchone()
    chain_rows=connection.execute("SELECT state_artifact FROM authorization_states WHERE network_id=? ORDER BY sequence_number", (public['network_id'],)).fetchall()
    available_states = ([cbor2.loads(anchor_row[0])] if anchor_row else []) + [cbor2.loads(row[0]) for row in chain_rows]
    if not available_states:
        available_states = [state]
    chain = _ordered_authorization_chain(available_states)
    compressed=zstandard.ZstdCompressor(level=3).compress(cbor2.dumps({'versao':2,'itens':items,'anexos':[],'cadeia_arka':chain},canonical=True))
    encrypted=AESGCM(key).encrypt(nonce,compressed,export_id.encode())
    envelopes=[]
    # Um membro revogado também recebe o envelope quando o arquivo lhe for
    # entregue manualmente. Isso permite que a cópia aplique a revogação; ela
    # interrompe a importação antes de persistir qualquer conteúdo.
    for member in recipients:
        ephemeral=x25519.X25519PrivateKey.generate(); salt=os.urandom(16); shared=ephemeral.exchange(x25519.X25519PublicKey.from_public_bytes(member['chave_cifragem'])); wrap=HKDF(algorithm=hashes.SHA256(),length=32,salt=export_id.encode(),info=b'Arkan ARKX v2 envelope').derive(shared); wrap_nonce=os.urandom(12)
        envelopes.append({'destinatario_id':member['membro_id'],'chave_efemera':ephemeral.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw),'salt':salt,'nonce':wrap_nonce,'chave_cifrada':AESGCM(wrap).encrypt(wrap_nonce,key,export_id.encode())})
    header={'versao':VERSION,'rede_id':public['network_id'],'exportacao_id':export_id,'exportador_id':public['member_id'],'emitido_em':_time(),'modalidade':mode,'nonce':nonce,'tamanho_carga':len(encrypted),'envelopes':envelopes,'assinatura_exportador':b''}
    private=ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(identity['signing_private_key'])); header['assinatura_exportador']=private.sign(_unsigned(header))
    encoded_header=cbor2.dumps(header,canonical=True)
    if len(encoded_header)>65536: raise ArkxError('Cabeçalho excede o limite.')
    artifact=MAGIC+bytes([VERSION])+len(encoded_header).to_bytes(4,'big')+encoded_header+encrypted
    if len(artifact)>MAX_FILE: raise ArkxError('Exportação excede o limite.')
    return artifact

def migrate_storage_schema(connection, version):
    if version < 9:
        from backend.database import migrate_local_classification_schema
        migrate_local_classification_schema(connection)
    if version < 10:
        connection.execute("DROP TABLE IF EXISTS attachments")

def read_export(connection, raw: bytes, identity: dict) -> dict:
    """Abre `ARKX v2` em memória, antes de qualquer persistência."""
    if not isinstance(raw, bytes) or len(raw) > MAX_FILE or not raw.startswith(MAGIC + bytes([VERSION])) or len(raw) < 9:
        raise ArkxError('O arquivo não é uma exportação ARKX v2 válida.')
    size=int.from_bytes(raw[5:9],'big')
    if size > 65536 or 9 + size >= len(raw): raise ArkxError('O cabeçalho da exportação é inválido.')
    try:
        header=cbor2.loads(raw[9:9+size])
        if not isinstance(header, dict):
            raise ValueError()
    except Exception as error:
        raise ArkxError('O cabeçalho da exportação é inválido.') from error
    try:
        encrypted=raw[9+size:]
        public=identity['public_identity']
        if header.get('versao') != VERSION or header.get('tamanho_carga') != len(encrypted):
            raise ArkxError('O cabeçalho da exportação é inválido.')
        if header.get('rede_id') != public['network_id']:
            raise ArkxError('Esta exportação pertence a outra rede.')
        state = _latest_authorization(connection, public['network_id'])
        exporter=next((member for member in state['membros'] if member['membro_id']==header.get('exportador_id') and member['status']=='ATIVO'),None)
        if exporter is None:
            raise ArkxError('O exportador não é um membro ativo reconhecido por esta cópia.')
        try:
            ed25519.Ed25519PublicKey.from_public_bytes(exporter['chave_assinatura']).verify(header['assinatura_exportador'],_unsigned(header))
        except Exception as error:
            raise ArkxError('A assinatura do exportador é inválida.') from error
        envelope=next((item for item in header.get('envelopes', []) if isinstance(item, dict) and item.get('destinatario_id')==public['member_id']), None)
        if envelope is None:
            raise ArkxError('Esta exportação não foi destinada a este membro.')
        private=x25519.X25519PrivateKey.from_private_bytes(base64.b64decode(identity['encryption_private_key']))
        shared=private.exchange(x25519.X25519PublicKey.from_public_bytes(envelope['chave_efemera']))
        wrap=HKDF(algorithm=hashes.SHA256(),length=32,salt=header['exportacao_id'].encode(),info=b'Arkan ARKX v2 envelope').derive(shared)
        try:
            key=AESGCM(wrap).decrypt(envelope['nonce'],envelope['chave_cifrada'],header['exportacao_id'].encode())
            packed=AESGCM(key).decrypt(header['nonce'],encrypted,header['exportacao_id'].encode())
        except Exception as error:
            raise ArkxError('Não foi possível abrir a exportação destinada a este membro.') from error
    except Exception as error:
        if isinstance(error, ArkxError):
            raise
        raise ArkxError('O cabeçalho da exportação é inválido.') from error
    try:
        payload=cbor2.loads(zstandard.ZstdDecompressor().decompress(packed,max_output_size=256*1024*1024))
        if not isinstance(payload,dict) or payload.get('versao')!=2 or not isinstance(payload.get('itens'),list) or not isinstance(payload.get('anexos'),list) or not isinstance(payload.get('cadeia_arka'),list): raise ValueError()
        if payload['anexos']:
            raise ArkxError('Esta exportação contém anexos não suportados.')
        return payload
    except Exception as error:
        raise ArkxError('O conteúdo protegido da exportação é inválido.') from error

def import_items(connection, identity: dict, payload: dict) -> dict[str, int]:
    """Importa a cadeia v2 antes do conteúdo publicado diretamente."""
    try:
        chain = payload['cadeia_arka']; public = identity['public_identity']
        if not chain: raise ValueError()
        previous = None
        for state in chain:
            validate_authorization_v2(state)
            if state['rede_id'] != public['network_id'] or (previous and (state['sequencia'] != previous['sequencia'] + 1 or state['anterior_hash'] != artifact_hash(previous))): raise ValueError()
            previous = state
        local_states = _local_authorizations(connection, public['network_id'])
        overlaps = [item for item in chain if item['sequencia'] in local_states]
        if any(artifact_hash(item) != artifact_hash(local_states[item['sequencia']]) for item in overlaps):
            raise ArkxError('Cadeia de autorização incompatível com a cópia local.')
        starts_after_local = (
            chain[0]['sequencia'] > 1
            and chain[0]['sequencia'] - 1 in local_states
            and chain[0]['anterior_hash'] == artifact_hash(local_states[chain[0]['sequencia'] - 1])
        )
        ends_before_local = (
            chain[-1]['sequencia'] + 1 in local_states
            and local_states[chain[-1]['sequencia'] + 1]['anterior_hash'] == artifact_hash(chain[-1])
        )
        if not overlaps and not starts_after_local and not ends_before_local:
            raise ArkxError('Cadeia de autorização incompatível com a cópia local.')
        highest_local = local_states[max(local_states)]
        has_newer_state = chain[-1]['sequencia'] > highest_local['sequencia']
        state = chain[-1] if has_newer_state else highest_local
        try:
            if has_newer_state:
                connection.execute("INSERT OR IGNORE INTO networks(network_id,guardian_member_id,created_at) VALUES (?, ?, ?)", (state['rede_id'], state['guardiao_id'], state['emitido_em']))
            for member in state['membros']:
                values = (member['membro_id'], state['rede_id'], base64.b64encode(member['chave_assinatura']).decode(), base64.b64encode(member['chave_cifragem']).decode(), member['papel'], member['status'], base64.b64encode(member['ativacao_hash']).decode(), member['efetivo_em'])
                if has_newer_state:
                    connection.execute(
                        """INSERT INTO members(member_id,network_id,signing_public_key,encryption_public_key,role,status,activation_hash,created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(member_id) DO UPDATE SET
                             network_id=excluded.network_id,
                             signing_public_key=excluded.signing_public_key,
                             encryption_public_key=excluded.encryption_public_key,
                             role=excluded.role,
                             status=excluded.status,
                             activation_hash=excluded.activation_hash,
                             created_at=excluded.created_at""",
                        values,
                    )
                else:
                    connection.execute(
                        "INSERT OR IGNORE INTO members(member_id,network_id,signing_public_key,encryption_public_key,role,status,activation_hash,created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        values,
                    )
            for state_item in chain:
                encoded=cbor2.dumps(state_item,canonical=True)
                connection.execute("INSERT OR IGNORE INTO authorization_states(network_id,sequence_number,state_hash,state_artifact,created_at) VALUES (?, ?, ?, ?, ?)", (state_item['rede_id'],state_item['sequencia'],artifact_hash(state_item),encoded,state_item['emitido_em']))
        except Exception as error:
            raise ArkxError('Não foi possível atualizar o estado de autorização local.') from error
    except ArkxError:
        raise
    except Exception as error:
        raise ArkxError('Estado de autorização inválido.') from error
    local_member = next((member for member in state['membros'] if member['membro_id'] == public['member_id']), None)
    if local_member is None or local_member['status'] != 'ATIVO':
        return {
            'status': 'COPIA_REVOGADA',
            'aceitos': 0,
            'duplicados': 0,
            'rejeitados': 0,
            'antecessores_indisponiveis': 0,
        }
    accepted=duplicate=rejected=missing_predecessor=0
    for item in payload['itens']:
        try:
            required={'hash','autor_id','sequencia','tipo','artigo_id','titulo','anterior_hash','criado_em','assinatura','assinatura_cabecalho'}
            if not isinstance(item,dict) or set(item) not in (required,required|{'corpo'}) or item['tipo'] not in {'ARTIGO','COMENTARIO'}: raise ValueError()
            author=next((m for m in state['membros'] if m['membro_id']==item['autor_id']),None)
            header={'versao':1,'rede_id':state['rede_id'],'autor_id':item['autor_id'],'tipo':item['tipo'],'sequencia':item['sequencia'],'artigo_id':item['artigo_id'],'titulo':item['titulo'],'anterior_hash':item['anterior_hash'],'criado_em':item['criado_em'],'conteudo_hash':item['hash']}
            content={key:value for key,value in header.items() if key != 'conteudo_hash'} | {'corpo':item.get('corpo','')}
            canonical=cbor2.dumps(content,canonical=True)
            if author is None or (author['status'] == 'REVOGADO' and item['criado_em'] >= author['revogado_em']): raise ValueError()
            verifier=ed25519.Ed25519PublicKey.from_public_bytes(author['chave_assinatura'])
            verifier.verify(item['assinatura_cabecalho'],cbor2.dumps(header,canonical=True))
            if 'corpo' in item:
                if hashlib.sha256(canonical).hexdigest()!=item['hash']: raise ValueError()
                verifier.verify(item['assinatura'],canonical)
            if connection.execute("SELECT 1 FROM publications WHERE content_hash=?",(item['hash'],)).fetchone(): duplicate+=1; continue
            from backend.library import register_header
            register_header(connection,item)
            if 'corpo' in item: connection.execute("INSERT INTO publications(content_hash,author_member_id,sequence_number,content_type,article_id,title,body,previous_publication_hash,signature,header_signature,created_at,publication_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PUBLICADO')",(item['hash'],item['autor_id'],item['sequencia'],item['tipo'],item['artigo_id'],item['titulo'],item['corpo'],item['anterior_hash'],item['assinatura'],item['assinatura_cabecalho'],item['criado_em']))
            accepted+=1
        except Exception: rejected+=1
    return {'aceitos':accepted,'duplicados':duplicate,'rejeitados':rejected,'antecessores_indisponiveis':missing_predecessor}

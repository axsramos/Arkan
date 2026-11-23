"""Controles locais de acervo sem propagação de remoções."""

from pathlib import Path

import cbor2

class LibraryError(RuntimeError): pass


def _pseudonyms(connection, network_id: str | None) -> dict[str, str]:
    """Obtém pseudônimos públicos do último estado assinado disponível."""
    if not network_id:
        return {}
    row = connection.execute(
        "SELECT state_artifact FROM authorization_states WHERE network_id=? ORDER BY sequence_number DESC LIMIT 1",
        (network_id,),
    ).fetchone()
    if row is None:
        row = connection.execute("SELECT state_artifact FROM authorization_anchors WHERE network_id=?", (network_id,)).fetchone()
    try:
        state = cbor2.loads(row[0]) if row else {}
        return {member['membro_id']: member['pseudonimo'] for member in state.get('membros', []) if isinstance(member, dict) and isinstance(member.get('membro_id'), str) and isinstance(member.get('pseudonimo'), str)}
    except Exception:
        return {}

def register_header(connection, item: dict) -> None:
    """Registra somente metadados resumidos, preservando cabeçalho existente."""
    connection.execute("INSERT OR IGNORE INTO content_headers(content_hash,author_member_id,sequence_number,content_type,parent_hash,previous_version_hash,title,created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (item['hash'],item['autor_id'],item['sequencia'],item['tipo'],item.get('artigo_id'),item.get('anterior_hash'),item.get('titulo'),item['criado_em']))
    connection.execute("INSERT OR IGNORE INTO local_content_control(content_hash) VALUES (?)",(item['hash'],))

def remove_foreign_content(connection, local_member_id: str, role: str, content_hash: str, attachment_dir: Path | None = None) -> None:
    row=connection.execute("SELECT author_member_id FROM content_headers WHERE content_hash=?",(content_hash,)).fetchone()
    if row is None or row[0]==local_member_id or role=='GUARDIAO':
        raise LibraryError('Remoção local não permitida.')
    attachment_names = [
        row[0] for row in connection.execute("SELECT storage_name FROM attachments WHERE article_hash=?", (content_hash,))
    ]
    connection.execute("DELETE FROM attachments WHERE article_hash=?", (content_hash,))
    connection.execute("DELETE FROM publications WHERE content_hash=?", (content_hash,))
    connection.execute("UPDATE local_content_control SET removed_locally=1 WHERE content_hash=?",(content_hash,))
    if attachment_dir is not None:
        for storage_name in attachment_names:
            (attachment_dir / storage_name).unlink(missing_ok=True)

def allow_reimport(connection, content_hash: str) -> None:
    if connection.execute("UPDATE local_content_control SET removed_locally=0 WHERE content_hash=?",(content_hash,)).rowcount != 1:
        raise LibraryError('Cabeçalho indisponível.')


def list_headers(connection, local_member_id: str, membership_status: str, network_id: str | None = None) -> list[dict]:
    """Lista metadados locais sem revelar corpo, chaves ou material de cofre."""
    query = """WITH known_headers AS (
            SELECT content_hash,author_member_id,sequence_number,content_type,parent_hash,previous_version_hash,title,created_at
            FROM content_headers
            UNION ALL
            SELECT p.content_hash,p.author_member_id,p.sequence_number,p.content_type,p.article_id,p.previous_publication_hash,p.title,p.created_at
            FROM publications p
            WHERE NOT EXISTS (SELECT 1 FROM content_headers h WHERE h.content_hash=p.content_hash)
        )
        SELECT h.content_hash,h.author_member_id,h.sequence_number,h.content_type,h.title,h.created_at,COALESCE(c.removed_locally,0),
        EXISTS(SELECT 1 FROM publications p WHERE p.content_hash=h.content_hash),category.category,
        (SELECT COUNT(DISTINCT comments.content_hash) FROM known_headers comments WHERE comments.content_type='COMENTARIO' AND comments.parent_hash=h.content_hash),
        EXISTS(SELECT 1 FROM export_items exports WHERE exports.content_hash=h.content_hash)
        FROM known_headers h
        LEFT JOIN local_content_control c ON c.content_hash=h.content_hash
        LEFT JOIN local_article_categories category ON category.article_hash=h.content_hash"""
    parameters: tuple = ()
    if membership_status != 'ATIVO':
        query += " WHERE h.author_member_id=?"
        parameters = (local_member_id,)
    query += " ORDER BY h.created_at DESC"
    pseudonyms = _pseudonyms(connection, network_id)
    headers = []
    for row in connection.execute(query, parameters):
        badges = [badge[0] for badge in connection.execute("SELECT label FROM local_article_badges WHERE article_hash=? ORDER BY label COLLATE NOCASE", (row[0],))] if row[3] == 'ARTIGO' else []
        headers.append({"hash": row[0], "autor_id": row[1], "autor_pseudonimo": pseudonyms.get(row[1]), "sequencia": row[2], "tipo": row[3], "titulo": row[4], "criado_em": row[5], "removido_localmente": bool(row[6]), "tem_corpo": bool(row[7]), "categoria": row[8], "comentarios": row[9], "exportado": bool(row[10]), "badges": badges, "proprio": row[1] == local_member_id})
    return headers


def read_content(connection, local_member_id: str, membership_status: str, content_hash: str, network_id: str | None = None) -> dict:
    """Retorna publicação local completa somente quando seu corpo foi recebido."""
    row = connection.execute(
        """SELECT h.content_hash,h.author_member_id,h.sequence_number,h.content_type,h.parent_hash,h.previous_version_hash,h.title,h.created_at,
            p.body,c.removed_locally
           FROM content_headers h
           JOIN local_content_control c ON c.content_hash=h.content_hash
           LEFT JOIN publications p ON p.content_hash=h.content_hash
           WHERE h.content_hash=?""",
        (content_hash,),
    ).fetchone()
    if row is None or (membership_status != 'ATIVO' and row[1] != local_member_id):
        raise LibraryError('Conteúdo indisponível.')
    return {
        "hash": row[0], "autor_id": row[1], "sequencia": row[2], "tipo": row[3], "artigo_hash": row[4],
        "anterior_hash": row[5], "titulo": row[6], "criado_em": row[7], "corpo": row[8],
        "removido_localmente": bool(row[9]), "tem_corpo": row[8] is not None, "proprio": row[1] == local_member_id,
        "autor_pseudonimo": _pseudonyms(connection, network_id).get(row[1]),
    }


def list_comments(connection, local_member_id: str, membership_status: str, article_hash: str, network_id: str | None = None) -> list[dict]:
    """Lista comentários conhecidos de um artigo, sem burlar remoção local."""
    rows = connection.execute(
        """SELECT h.content_hash,h.author_member_id,h.created_at,p.body,c.removed_locally
           FROM content_headers h
           JOIN local_content_control c ON c.content_hash=h.content_hash
           LEFT JOIN publications p ON p.content_hash=h.content_hash
           WHERE h.content_type='COMENTARIO' AND h.parent_hash=?
           ORDER BY h.created_at ASC""",
        (article_hash,),
    )
    pseudonyms = _pseudonyms(connection, network_id)
    comments = []
    for row in rows:
        if membership_status != 'ATIVO' and row[1] != local_member_id:
            continue
        comments.append({
            'hash': row[0], 'autor_id': row[1], 'autor_pseudonimo': pseudonyms.get(row[1]), 'criado_em': row[2], 'corpo': row[3],
            'removido_localmente': bool(row[4]), 'tem_corpo': row[3] is not None,
            'proprio': row[1] == local_member_id,
        })
    return comments


def get_local_classification(connection, article_hash: str) -> dict:
    article = connection.execute("SELECT content_type FROM content_headers WHERE content_hash=?", (article_hash,)).fetchone()
    if article is None or article[0] != 'ARTIGO':
        raise LibraryError('Artigo indisponível.')
    category = connection.execute("SELECT category FROM local_article_categories WHERE article_hash=?", (article_hash,)).fetchone()
    badges = [row[0] for row in connection.execute("SELECT label FROM local_article_badges WHERE article_hash=? ORDER BY label COLLATE NOCASE", (article_hash,))]
    categories = [row[0] for row in connection.execute("SELECT DISTINCT category FROM local_article_categories ORDER BY category COLLATE NOCASE")]
    return {'categoria': category[0] if category else None, 'badges': badges, 'categorias_disponiveis': categories}


def set_local_classification(connection, article_hash: str, category: str | None, badges: list[str]) -> dict:
    get_local_classification(connection, article_hash)
    normalized_category = category.strip() if isinstance(category, str) else None
    if normalized_category == '':
        normalized_category = None
    if normalized_category is not None and len(normalized_category) > 80:
        raise LibraryError('Categoria local inválida.')
    if not isinstance(badges, list) or len(badges) > 20:
        raise LibraryError('Badges locais inválidos.')
    normalized_badges = []
    seen = set()
    for badge in badges:
        if not isinstance(badge, str):
            raise LibraryError('Badges locais inválidos.')
        label = badge.strip()
        if not label or len(label) > 40 or label.casefold() in seen:
            raise LibraryError('Badges locais inválidos.')
        seen.add(label.casefold())
        normalized_badges.append(label)
    if normalized_category is None:
        connection.execute("DELETE FROM local_article_categories WHERE article_hash=?", (article_hash,))
    else:
        connection.execute("INSERT INTO local_article_categories(article_hash,category) VALUES (?,?) ON CONFLICT(article_hash) DO UPDATE SET category=excluded.category", (article_hash, normalized_category))
    connection.execute("DELETE FROM local_article_badges WHERE article_hash=?", (article_hash,))
    connection.executemany("INSERT INTO local_article_badges(article_hash,label) VALUES (?,?)", [(article_hash, badge) for badge in normalized_badges])
    return get_local_classification(connection, article_hash)

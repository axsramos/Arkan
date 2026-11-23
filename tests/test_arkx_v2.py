import base64
import hashlib
import os
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import cbor2
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.arkx import ArkxError, _ordered_authorization_chain, build_export, import_items, read_export
from backend.database import initialize_schema
from backend.protocol import artifact_hash, sign_authorization_v2


def timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ArkxV2Tests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        initialize_schema(self.connection)
        self.network_id = str(uuid4())
        self.member_id = str(uuid4())
        self.key = Ed25519PrivateKey.generate()
        self.public_key = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.identity = {"public_identity": {"network_id": self.network_id, "member_id": self.member_id}}
        self.authorization = self.state()
        self.connection.execute(
            "INSERT INTO networks(network_id, guardian_member_id, created_at) VALUES (?, ?, ?)",
            (self.network_id, self.member_id, self.authorization["emitido_em"]),
        )
        self.connection.execute(
            "INSERT INTO authorization_anchors(network_id, sequence_number, state_hash, state_artifact, anchored_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 1, hashlib.sha256(cbor2.dumps(self.authorization, canonical=True)).digest(), cbor2.dumps(self.authorization, canonical=True), self.authorization["emitido_em"]),
        )

    def tearDown(self):
        self.connection.close()

    def state(self, status="ATIVO"):
        issued = timestamp()
        return sign_authorization_v2({
            "tipo": "ARKA", "versao": 2, "rede_id": self.network_id, "guardiao_id": self.member_id,
            "guardiao_chave_assinatura": self.public_key, "sequencia": 1, "anterior_hash": None,
            "emitido_em": issued,
            "membros": [{"membro_id": self.member_id, "pseudonimo": "Guardião", "papel": "GUARDIAO", "status": status,
                "chave_assinatura": self.public_key, "chave_cifragem": os.urandom(32), "ativacao_hash": os.urandom(32),
                "efetivo_em": issued, "revogado_em": None if status == "ATIVO" else issued}],
            "assinatura": b"",
        }, self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))

    def item(self):
        content = {"versao": 1, "rede_id": self.network_id, "autor_id": self.member_id, "tipo": "ARTIGO", "sequencia": 1,
                   "artigo_id": None, "titulo": "Título", "corpo": "Corpo", "anterior_hash": None, "criado_em": timestamp()}
        canonical = cbor2.dumps(content, canonical=True)
        content_hash = hashlib.sha256(canonical).hexdigest()
        header = {key: value for key, value in content.items() if key != "corpo"} | {"conteudo_hash": content_hash}
        return {"hash": content_hash, "autor_id": self.member_id, "sequencia": 1,
                "tipo": "ARTIGO", "artigo_id": None, "titulo": "Título", "anterior_hash": None,
                "criado_em": content["criado_em"], "assinatura": self.key.sign(canonical),
                "assinatura_cabecalho": self.key.sign(cbor2.dumps(header, canonical=True)), "corpo": "Corpo"}

    def test_imports_authorized_direct_publication(self):
        result = import_items(self.connection, self.identity, {"cadeia_arka": [self.authorization], "itens": [self.item()]})
        self.assertEqual(result["aceitos"], 1)
        self.assertEqual(self.connection.execute("SELECT publication_status FROM publications").fetchone()[0], "PUBLICADO")

    def test_rejects_missing_authorization_chain(self):
        with self.assertRaises(ArkxError):
            import_items(self.connection, self.identity, {"cadeia_arka": [], "itens": []})

    def test_blocks_local_copy_already_marked_as_revoked(self):
        self.connection.execute("DELETE FROM authorization_anchors")
        authorization = self.state("REVOGADO")
        self.connection.execute(
            "INSERT INTO authorization_anchors(network_id, sequence_number, state_hash, state_artifact, anchored_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 1, hashlib.sha256(cbor2.dumps(authorization, canonical=True)).digest(), cbor2.dumps(authorization, canonical=True), authorization["emitido_em"]),
        )
        result = import_items(self.connection, self.identity, {"cadeia_arka": [authorization], "itens": [self.item()]})
        self.assertEqual(result["status"], "COPIA_REVOGADA")
        self.assertEqual(self.connection.execute("SELECT count(*) FROM publications").fetchone()[0], 0)

    def test_does_not_import_old_content_after_local_revocation(self):
        self.connection.execute("DELETE FROM authorization_anchors")
        authorization = self.state("REVOGADO")
        self.connection.execute(
            "INSERT INTO authorization_anchors(network_id, sequence_number, state_hash, state_artifact, anchored_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 1, hashlib.sha256(cbor2.dumps(authorization, canonical=True)).digest(), cbor2.dumps(authorization, canonical=True), authorization["emitido_em"]),
        )
        item = self.item()
        item["criado_em"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        content = {"versao": 1, "rede_id": self.network_id, "autor_id": self.member_id, "tipo": "ARTIGO", "sequencia": 1, "artigo_id": None, "titulo": "Título", "corpo": "Corpo", "anterior_hash": None, "criado_em": item["criado_em"]}
        canonical = cbor2.dumps(content, canonical=True)
        item["hash"] = hashlib.sha256(canonical).hexdigest()
        header = {key: value for key, value in content.items() if key != "corpo"} | {"conteudo_hash": item["hash"]}
        item["assinatura"] = self.key.sign(canonical)
        item["assinatura_cabecalho"] = self.key.sign(cbor2.dumps(header, canonical=True))
        result = import_items(self.connection, self.identity, {"cadeia_arka": [authorization], "itens": [item]})
        self.assertEqual(result["status"], "COPIA_REVOGADA")

    def test_rejects_chain_with_invalid_signature_before_persisting(self):
        authorization = deepcopy(self.authorization)
        authorization["assinatura"] = b"\x00" * 64

        with self.assertRaises(ArkxError):
            import_items(self.connection, self.identity, {"cadeia_arka": [authorization], "itens": []})

        self.assertEqual(self.connection.execute("SELECT count(*) FROM authorization_states").fetchone()[0], 0)

    def test_rejects_chain_that_does_not_contain_local_anchor(self):
        authorization = deepcopy(self.authorization)
        authorization["membros"][0]["ativacao_hash"] = os.urandom(32)
        authorization = sign_authorization_v2(
            {**authorization, "assinatura": b""},
            self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()),
        )

        with self.assertRaises(ArkxError):
            import_items(self.connection, self.identity, {"cadeia_arka": [authorization], "itens": []})

    def test_accepts_verified_summary_header_without_body(self):
        item = self.item()
        item.pop("corpo")
        result = import_items(self.connection, self.identity, {"cadeia_arka": [self.authorization], "itens": [item]})

        self.assertEqual(result["aceitos"], 1)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM content_headers").fetchone()[0], 1)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM publications").fetchone()[0], 0)

    def test_revoked_recipient_applies_state_without_importing_content(self):
        """A cópia revogada abre o ARKX apenas para aplicar a própria revogação."""
        recipient_id = str(uuid4())
        recipient_signing = Ed25519PrivateKey.generate()
        recipient_encryption = x25519.X25519PrivateKey.generate()
        issued = timestamp()
        authorization = sign_authorization_v2(
            {
                "tipo": "ARKA", "versao": 2, "rede_id": self.network_id,
                "guardiao_id": self.member_id, "guardiao_chave_assinatura": self.public_key,
                "sequencia": 1, "anterior_hash": None, "emitido_em": issued,
                "membros": [
                    self.authorization["membros"][0],
                    {
                        "membro_id": recipient_id, "pseudonimo": "Membro", "papel": "MEMBRO",
                        "status": "ATIVO",
                        "chave_assinatura": recipient_signing.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
                        "chave_cifragem": recipient_encryption.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
                        "ativacao_hash": os.urandom(32), "efetivo_em": issued, "revogado_em": None,
                    },
                ],
                "assinatura": b"",
            },
            self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()),
        )
        self.connection.execute("DELETE FROM authorization_anchors")
        self.connection.execute(
            "INSERT INTO authorization_anchors(network_id, sequence_number, state_hash, state_artifact, anchored_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 1, hashlib.sha256(cbor2.dumps(authorization, canonical=True)).digest(), cbor2.dumps(authorization, canonical=True), issued),
        )
        for member in authorization["membros"]:
            self.connection.execute(
                "INSERT INTO members(member_id,network_id,signing_public_key,encryption_public_key,role,status,activation_hash,created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (member["membro_id"], self.network_id, base64.b64encode(member["chave_assinatura"]).decode(), base64.b64encode(member["chave_cifragem"]).decode(), member["papel"], member["status"], base64.b64encode(member["ativacao_hash"]).decode(), member["efetivo_em"]),
            )
        source_identity = {
            "public_identity": {"network_id": self.network_id, "member_id": self.member_id},
            "signing_private_key": base64.b64encode(self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())).decode(),
        }
        self.connection.execute(
            "INSERT INTO publications(content_hash,author_member_id,sequence_number,content_type,article_id,title,body,previous_publication_hash,signature,header_signature,created_at,publication_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PUBLICADO')",
            tuple(self.item()[key] for key in ("hash", "autor_id", "sequencia", "tipo", "artigo_id", "titulo", "corpo", "anterior_hash", "assinatura", "assinatura_cabecalho", "criado_em")),
        )
        revoked_members = deepcopy(authorization["membros"])
        revoked_members[1]["status"] = "REVOGADO"
        revoked_members[1]["revogado_em"] = timestamp()
        revoked = sign_authorization_v2(
            {
                **authorization,
                "sequencia": 2,
                "anterior_hash": artifact_hash(authorization),
                "emitido_em": timestamp(),
                "membros": revoked_members,
                "assinatura": b"",
            },
            self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()),
        )
        self.connection.execute(
            "INSERT INTO authorization_states(network_id,sequence_number,state_hash,state_artifact,created_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 2, artifact_hash(revoked), cbor2.dumps(revoked, canonical=True), revoked["emitido_em"]),
        )
        raw = build_export(self.connection, source_identity)
        recipient_connection = sqlite3.connect(":memory:")
        self.addCleanup(recipient_connection.close)
        initialize_schema(recipient_connection)
        recipient_connection.execute(
            "INSERT INTO networks(network_id, guardian_member_id, created_at) VALUES (?, ?, ?)",
            (self.network_id, self.member_id, issued),
        )
        recipient_connection.execute(
            "INSERT INTO authorization_anchors(network_id, sequence_number, state_hash, state_artifact, anchored_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 1, hashlib.sha256(cbor2.dumps(authorization, canonical=True)).digest(), cbor2.dumps(authorization, canonical=True), issued),
        )
        recipient_identity = {
            "public_identity": {"network_id": self.network_id, "member_id": recipient_id},
            "encryption_private_key": base64.b64encode(recipient_encryption.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())).decode(),
        }
        payload = read_export(recipient_connection, raw, recipient_identity)
        result = import_items(recipient_connection, recipient_identity, payload)

        self.assertEqual(result["status"], "COPIA_REVOGADA")
        self.assertEqual(recipient_connection.execute("SELECT status FROM members WHERE member_id=?", (recipient_id,)).fetchone()[0], "REVOGADO")
        self.assertEqual(recipient_connection.execute("SELECT count(*) FROM publications").fetchone()[0], 0)

    def test_export_orders_history_received_before_local_anchor(self):
        """A âncora tardia não pode colocar o histórico em ordem inválida no ARKX."""
        second = sign_authorization_v2(
            {**self.authorization, "sequencia": 2, "anterior_hash": hashlib.sha256(cbor2.dumps({key: value for key, value in self.authorization.items() if key != "assinatura"}, canonical=True)).digest(), "emitido_em": timestamp(), "assinatura": b""},
            self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()),
        )
        self.connection.execute("DELETE FROM authorization_anchors")
        self.connection.execute(
            "INSERT INTO authorization_anchors(network_id, sequence_number, state_hash, state_artifact, anchored_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 2, hashlib.sha256(cbor2.dumps(second, canonical=True)).digest(), cbor2.dumps(second, canonical=True), second["emitido_em"]),
        )
        self.connection.execute(
            "INSERT INTO authorization_states(network_id, sequence_number, state_hash, state_artifact, created_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 1, hashlib.sha256(cbor2.dumps(self.authorization, canonical=True)).digest(), cbor2.dumps(self.authorization, canonical=True), self.authorization["emitido_em"]),
        )
        self.connection.execute(
            "INSERT INTO authorization_states(network_id, sequence_number, state_hash, state_artifact, created_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 2, hashlib.sha256(cbor2.dumps(second, canonical=True)).digest(), cbor2.dumps(second, canonical=True), second["emitido_em"]),
        )
        identity = {
            "public_identity": {"network_id": self.network_id, "member_id": self.member_id},
            "signing_private_key": base64.b64encode(self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())).decode(),
        }

        self.assertEqual([item["sequencia"] for item in _ordered_authorization_chain([second, self.authorization, second])], [1, 2])

    def test_accepts_export_chain_behind_local_state(self):
        """Um arquivo anterior não pode ser recusado só porque o receptor sabe mais."""
        second = sign_authorization_v2(
            {**self.authorization, "sequencia": 2, "anterior_hash": hashlib.sha256(cbor2.dumps({key: value for key, value in self.authorization.items() if key != "assinatura"}, canonical=True)).digest(), "emitido_em": timestamp(), "assinatura": b""},
            self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()),
        )
        self.connection.execute(
            "INSERT INTO authorization_states(network_id, sequence_number, state_hash, state_artifact, created_at) VALUES (?, ?, ?, ?, ?)",
            (self.network_id, 2, hashlib.sha256(cbor2.dumps(second, canonical=True)).digest(), cbor2.dumps(second, canonical=True), second["emitido_em"]),
        )

        result = import_items(self.connection, self.identity, {"cadeia_arka": [self.authorization], "itens": [self.item()]})

        self.assertEqual(result["aceitos"], 1)

    def test_accepts_contiguous_newer_chain_without_repeated_anchor(self):
        """Uma cópia que ancorou no ingresso pode enviar apenas estados posteriores."""
        second = sign_authorization_v2(
            {**self.authorization, "sequencia": 2, "anterior_hash": hashlib.sha256(cbor2.dumps({key: value for key, value in self.authorization.items() if key != "assinatura"}, canonical=True)).digest(), "emitido_em": timestamp(), "assinatura": b""},
            self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()),
        )

        result = import_items(self.connection, self.identity, {"cadeia_arka": [second], "itens": [self.item()]})

        self.assertEqual(result["aceitos"], 1)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM authorization_states WHERE sequence_number=2").fetchone()[0], 1)

    def test_updates_member_state_without_removing_referenced_publication(self):
        """A atualização pública não pode apagar membro referenciado por conteúdo local."""
        member = self.authorization["membros"][0]
        self.connection.execute(
            "INSERT INTO members(member_id,network_id,signing_public_key,encryption_public_key,role,status,activation_hash,created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (member["membro_id"], self.network_id, base64.b64encode(member["chave_assinatura"]).decode(), base64.b64encode(member["chave_cifragem"]).decode(), member["papel"], member["status"], base64.b64encode(member["ativacao_hash"]).decode(), member["efetivo_em"]),
        )
        item = self.item()
        self.connection.execute(
            "INSERT INTO publications(content_hash,author_member_id,sequence_number,content_type,article_id,title,body,previous_publication_hash,signature,header_signature,created_at,publication_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PUBLICADO')",
            tuple(item[key] for key in ("hash", "autor_id", "sequencia", "tipo", "artigo_id", "titulo", "corpo", "anterior_hash", "assinatura", "assinatura_cabecalho", "criado_em")),
        )

        second = sign_authorization_v2(
            {**self.authorization, "sequencia": 2, "anterior_hash": hashlib.sha256(cbor2.dumps({key: value for key, value in self.authorization.items() if key != "assinatura"}, canonical=True)).digest(), "emitido_em": timestamp(), "assinatura": b""},
            self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()),
        )
        result = import_items(self.connection, self.identity, {"cadeia_arka": [self.authorization, second], "itens": []})

        self.assertEqual(result["aceitos"], 0)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM publications").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()

"""Rascunhos locais e publicações diretas imutáveis."""

import base64
import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import cbor2
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.library import register_header


class ContentError(RuntimeError):
    """Falha não sensível no ciclo local de conteúdo."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _author(connection: Any, identity: dict[str, Any]) -> tuple[str, str]:
    public = identity["public_identity"]
    row = connection.execute("SELECT status FROM members WHERE member_id = ?", (public["member_id"],)).fetchone()
    if row is None or row[0] != "ATIVO":
        raise ContentError("A autoria não está autorizada nesta cópia.")
    return public["network_id"], public["member_id"]


def list_drafts(connection: Any, identity: dict[str, Any]) -> list[dict[str, str | None]]:
    """Lista somente os rascunhos mutáveis da autoria local."""
    _, author_id = _author(connection, identity)
    rows = connection.execute(
        """SELECT draft_id,content_type,article_id,title,body,previous_publication_hash,review_status,created_at,updated_at
           FROM content_drafts WHERE author_member_id=? ORDER BY updated_at DESC""",
        (author_id,),
    )
    return [
        {
            "draft_id": row[0], "content_type": row[1], "article_id": row[2],
            "title": row[3], "body": row[4], "previous_hash": row[5], "status": row[6],
            "created_at": row[7], "updated_at": row[8],
        }
        for row in rows
    ]


def create_draft(connection: Any, identity: dict[str, Any], content_type: str, title: str | None, body: str, article_id: str | None = None, previous_hash: str | None = None) -> dict[str, str]:
    _, author_id = _author(connection, identity)
    if content_type not in {"ARTIGO", "COMENTARIO"} or not isinstance(body, str) or not body.strip():
        raise ContentError("Rascunho inválido.")
    if content_type == "ARTIGO" and (not isinstance(title, str) or not title.strip()):
        raise ContentError("Rascunho inválido.")
    if content_type == "COMENTARIO":
        article = connection.execute("SELECT content_type FROM publications WHERE content_hash = ?", (article_id,)).fetchone() if article_id else None
        if article is None or article[0] != "ARTIGO":
            raise ContentError("Comentário sem artigo inválido.")
    if previous_hash:
        previous = connection.execute("SELECT author_member_id, content_type FROM publications WHERE content_hash = ?", (previous_hash,)).fetchone()
        if previous is None or previous[0] != author_id or previous[1] != content_type:
            raise ContentError("Versão anterior inválida.")
    now, draft_id = _timestamp(), str(uuid4())
    connection.execute(
        """INSERT INTO content_drafts(
            draft_id,author_member_id,content_type,article_id,title,body,
            previous_publication_hash,review_status,created_at,updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (draft_id, author_id, content_type, article_id, title.strip() if title else None, body, previous_hash, "RASCUNHO", now, now),
    )
    return {"draft_id": draft_id}


def update_draft(connection: Any, identity: dict[str, Any], draft_id: str, title: str | None, body: str) -> None:
    _, author_id = _author(connection, identity)
    row = connection.execute("SELECT content_type, author_member_id FROM content_drafts WHERE draft_id = ?", (draft_id,)).fetchone()
    if row is None or row[1] != author_id or not isinstance(body, str) or not body.strip() or (row[0] == "ARTIGO" and (not isinstance(title, str) or not title.strip())):
        raise ContentError("Rascunho indisponível.")
    connection.execute("UPDATE content_drafts SET title = ?, body = ?, review_status = 'RASCUNHO', updated_at = ? WHERE draft_id = ?", (title.strip() if title else None, body, _timestamp(), draft_id))


def delete_draft(connection: Any, identity: dict[str, Any], draft_id: str) -> None:
    _, author_id = _author(connection, identity)
    result = connection.execute("DELETE FROM content_drafts WHERE draft_id = ? AND author_member_id = ? AND review_status = 'RASCUNHO'", (draft_id, author_id))
    if result.rowcount != 1:
        raise ContentError("Rascunho indisponível.")


def review_draft(connection: Any, identity: dict[str, Any], draft_id: str) -> None:
    """Move um rascunho local para a prévia somente leitura."""
    _, author_id = _author(connection, identity)
    result = connection.execute(
        "UPDATE content_drafts SET review_status = 'EM_REVISAO', updated_at = ? "
        "WHERE draft_id = ? AND author_member_id = ? AND review_status = 'RASCUNHO'",
        (_timestamp(), draft_id, author_id),
    )
    if result.rowcount != 1:
        raise ContentError("Rascunho indisponível para revisão.")


def publish_draft(connection: Any, identity: dict[str, Any], draft_id: str, confirmed: bool) -> dict[str, str | int]:
    network_id, author_id = _author(connection, identity)
    if confirmed is not True:
        raise ContentError("A confirmação de publicação é obrigatória.")
    draft = connection.execute("SELECT content_type, article_id, title, body, previous_publication_hash FROM content_drafts WHERE draft_id = ? AND author_member_id = ? AND review_status = 'EM_REVISAO'", (draft_id, author_id)).fetchone()
    if draft is None:
        raise ContentError("Rascunho indisponível.")
    sequence = connection.execute(
        "SELECT COALESCE(MAX(sequence_number), 0) FROM publications WHERE author_member_id = ?",
        (author_id,),
    ).fetchone()[0] + 1
    created_at = _timestamp()
    payload = {"versao": 1, "rede_id": network_id, "autor_id": author_id, "tipo": draft[0], "sequencia": sequence, "artigo_id": draft[1], "titulo": draft[2], "corpo": draft[3], "anterior_hash": draft[4], "criado_em": created_at}
    canonical = cbor2.dumps(payload, canonical=True)
    content_hash = hashlib.sha256(canonical).hexdigest()
    private_key = base64.b64decode(identity["signing_private_key"], validate=True)
    signer = Ed25519PrivateKey.from_private_bytes(private_key)
    signature = signer.sign(canonical)
    header = {key: value for key, value in payload.items() if key != "corpo"} | {"conteudo_hash": content_hash}
    header_signature = signer.sign(cbor2.dumps(header, canonical=True))
    connection.execute("INSERT INTO publications(content_hash,author_member_id,sequence_number,content_type,article_id,title,body,previous_publication_hash,signature,header_signature,created_at,publication_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PUBLICADO')", (content_hash, author_id, sequence, draft[0], draft[1], draft[2], draft[3], draft[4], signature, header_signature, created_at))
    register_header(connection, {**payload, "hash": content_hash})
    connection.execute("DELETE FROM content_drafts WHERE draft_id = ?", (draft_id,))
    return {"content_hash": content_hash, "sequence_number": sequence, "publication_status": "PUBLICADO"}

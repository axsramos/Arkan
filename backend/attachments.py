"""Validação mínima e armazenamento cifrado de anexos de artigos."""

import hashlib
import os
import base64
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import cbor2

from backend.content import ContentError, _author

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED = {
    b"%PDF-": "application/pdf", b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg", b"GIF87a": "image/gif", b"GIF89a": "image/gif",
}
ALLOWED_MEDIA_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/gif", "text/plain", "text/markdown"}


class AttachmentError(RuntimeError):
    """Falha não sensível na inclusão de anexo."""


def list_article_attachments(connection, article_hash: str) -> list[dict[str, str | int]]:
    """Expõe somente metadados; bytes de anexos nunca transitam pela interface."""
    return [
        {
            "attachment_id": row[0], "autor_id": row[1], "sequencia": row[2],
            "hash": row[3], "tipo_mime": row[4], "tamanho": row[5], "criado_em": row[6],
        }
        for row in connection.execute(
            """SELECT attachment_id,author_member_id,sequence_number,content_hash,media_type,size_bytes,created_at
               FROM attachments WHERE article_hash=? ORDER BY created_at ASC""",
            (article_hash,),
        )
    ]


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _detect(path: Path) -> tuple[bytes, str]:
    try:
        size = path.stat().st_size
        if size <= 0 or size > MAX_ATTACHMENT_SIZE:
            raise AttachmentError("Anexo inválido.")
        with path.open("rb") as source:
            header = source.read(16)
            source.seek(0)
            data = source.read()
    except OSError as error:
        raise AttachmentError("Anexo indisponível.") from error
    if header.startswith((b"MZ", b"#!")):
        raise AttachmentError("Anexo não permitido.")
    for signature, media_type in ALLOWED.items():
        if header.startswith(signature):
            return data, media_type
    if path.suffix.lower() in {".txt", ".md"}:
        return data, "text/markdown" if path.suffix.lower() == ".md" else "text/plain"
    raise AttachmentError("Anexo não permitido.")


def validate_imported_attachment(data: bytes, media_type: str) -> None:
    """Recusa código executável por cabeçalho, sem interpretar a carga recebida."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_ATTACHMENT_SIZE or media_type not in ALLOWED_MEDIA_TYPES:
        raise AttachmentError("Anexo inválido.")
    header = data[:16]
    if header.startswith((b"MZ", b"#!")):
        raise AttachmentError("Anexo não permitido.")
    detected = next((value for signature, value in ALLOWED.items() if header.startswith(signature)), None)
    if detected is not None and detected != media_type:
        raise AttachmentError("Anexo inválido.")
    if detected is None and media_type not in {"text/plain", "text/markdown"}:
        raise AttachmentError("Anexo inválido.")


def migrate_attachments(connection, version: int) -> int:
    from backend.database import migrate_attachment_schema, migrate_content_schema, migrate_member_management_schema
    if version < 2: migrate_member_management_schema(connection)
    if version < 3: migrate_content_schema(connection)
    if version < 4: migrate_attachment_schema(connection)
    return 4


def attach_to_article(connection, identity, data_key: bytes, article_hash: str, path: Path, target_dir: Path) -> dict[str, str | int]:
    network_id, author_id = _author(connection, identity)
    article = connection.execute("SELECT author_member_id, content_type FROM publications WHERE content_hash = ?", (article_hash,)).fetchone()
    if article is None or article[0] != author_id or article[1] != "ARTIGO":
        raise AttachmentError("Artigo indisponível para anexo.")
    data, media_type = _detect(path)
    attachment_hash = hashlib.sha256(data).hexdigest()
    sequence = max(
        connection.execute("SELECT COALESCE(MAX(sequence_number), 0) FROM publications WHERE author_member_id = ?", (author_id,)).fetchone()[0],
        connection.execute("SELECT COALESCE(MAX(sequence_number), 0) FROM attachments WHERE author_member_id = ?", (author_id,)).fetchone()[0],
    ) + 1
    created_at = _timestamp()
    metadata = {"versao": 1, "rede_id": network_id, "autor_id": author_id, "tipo": "ANEXO", "sequencia": sequence, "artigo_hash": article_hash, "conteudo_hash": attachment_hash, "tipo_mime": media_type, "tamanho": len(data), "criado_em": created_at}
    signature = Ed25519PrivateKey.from_private_bytes(base64.b64decode(identity["signing_private_key"], validate=True)).sign(cbor2.dumps(metadata, canonical=True))
    nonce, attachment_id = os.urandom(12), str(uuid4())
    storage_name = f"{attachment_id}.bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    temporary = target_dir / f".{storage_name}.tmp"
    final = target_dir / storage_name
    try:
        temporary.write_bytes(AESGCM(data_key).encrypt(nonce, data, article_hash.encode("ascii")))
        connection.execute("INSERT INTO attachments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (attachment_id, article_hash, author_id, sequence, attachment_hash, media_type, len(data), storage_name, nonce, signature, created_at))
        os.replace(temporary, final)
    except Exception:
        temporary.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        raise
    return {"attachment_id": attachment_id, "media_type": media_type, "size_bytes": len(data)}

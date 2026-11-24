"""Rotas locais para rascunhos, publicação direta e intercâmbio manual."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.content import ContentError, create_draft, delete_draft, list_drafts, publish_draft, review_draft, update_draft
from backend.arkx import ArkxError, build_export, migrate_storage_schema, read_export, import_items
from backend.library import LibraryError, remove_foreign_content, allow_reimport, get_local_classification, list_comments, list_headers, read_content, set_local_classification
from backend.native_dialog import save_export_artifact
from backend.data_store import FORMAT_VERSION, DataStoreError, migrate_data_store, open_data_store, _read_manifest
from backend.vault import VaultError
from backend.session import SESSION_COOKIE, SessionError, sessions
from backend.config import STORAGE_DIR

router = APIRouter()


class DraftPayload(BaseModel):
    content_type: Literal["ARTIGO", "COMENTARIO"]
    title: str | None = Field(default=None, max_length=240)
    body: str = Field(min_length=1, max_length=200000)
    article_id: str | None = None
    previous_hash: str | None = None


class DraftUpdatePayload(BaseModel):
    title: str | None = Field(default=None, max_length=240)
    body: str = Field(min_length=1, max_length=200000)


class DraftActionPayload(BaseModel):
    pass


class PublishPayload(DraftActionPayload):
    confirmed: bool

class ExportPayload(DraftActionPayload):
    since: str | None = None
    unexported_only: bool = False

class ContentHashPayload(DraftActionPayload):
    content_hash: str = Field(min_length=1, max_length=128)


class LocalClassificationPayload(DraftActionPayload):
    category: str | None = Field(default=None, max_length=80)
    badges: list[str] = Field(default_factory=list, max_length=20)


def _with_content(request: Request, operation):
    session = sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
    key = session.data_key
    connection = _open_content_store(key)
    try:
        member_id = session.identity["public_identity"]["member_id"]
        status_row = connection.execute("SELECT status FROM members WHERE member_id = ?", (member_id,)).fetchone()
        if status_row is None or status_row[0] != "ATIVO":
            raise ContentError("A sessão não está autorizada para alterar conteúdo.")
        result = operation(connection, session.identity)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _open_content_store(key: bytes):
    version = _read_manifest(Path(STORAGE_DIR))["format_version"]
    if version < FORMAT_VERSION:
        migrate_data_store(Path(STORAGE_DIR), key, FORMAT_VERSION, lambda connection: migrate_storage_schema(connection, version))
    return open_data_store(Path(STORAGE_DIR), key)


def _error(error: Exception):
    if isinstance(error, (VaultError, DataStoreError, SessionError)):
        return HTTPException(401, "Sessão local bloqueada.")
    return HTTPException(400, "A operação de conteúdo não pôde ser concluída.")


@router.get("/api/v1/content/library")
async def library(request: Request) -> dict:
    try:
        session = sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
        from backend.config import STORAGE_DIR
        connection = _open_content_store(session.data_key)
        try:
            public = session.identity["public_identity"]
            status_row = connection.execute("SELECT role,status FROM members WHERE member_id=?", (public["member_id"],)).fetchone()
            if status_row is None:
                raise ContentError("Acervo indisponível.")
            _, membership_status = status_row
            return {"itens": list_headers(connection, public["member_id"], membership_status, public["network_id"])}
        finally:
            connection.close()
    except (VaultError, DataStoreError, ContentError, SessionError) as error:
        raise _error(error)


@router.get("/api/v1/content/articles/{content_hash}")
async def article(content_hash: str, request: Request) -> dict:
    try:
        session = sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
        connection = _open_content_store(session.data_key)
        try:
            public = session.identity["public_identity"]
            status_row = connection.execute("SELECT status FROM members WHERE member_id=?", (public["member_id"],)).fetchone()
            if status_row is None:
                raise LibraryError("Conteúdo indisponível.")
            return read_content(connection, public["member_id"], status_row[0], content_hash, public["network_id"])
        finally:
            connection.close()
    except (VaultError, DataStoreError, LibraryError, SessionError) as error:
        raise _error(error)


@router.get("/api/v1/content/articles/{content_hash}/comments")
async def comments(content_hash: str, request: Request) -> dict:
    try:
        session = sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
        connection = _open_content_store(session.data_key)
        try:
            public = session.identity["public_identity"]
            status_row = connection.execute("SELECT status FROM members WHERE member_id=?", (public["member_id"],)).fetchone()
            if status_row is None:
                raise LibraryError("Conteúdo indisponível.")
            return {"comentarios": list_comments(connection, public["member_id"], status_row[0], content_hash, public["network_id"])}
        finally:
            connection.close()
    except (VaultError, DataStoreError, LibraryError, SessionError) as error:
        raise _error(error)


@router.get("/api/v1/content/articles/{content_hash}/classification")
async def local_classification(content_hash: str, request: Request) -> dict:
    try:
        return _with_content(request, lambda connection, identity: get_local_classification(connection, content_hash))
    except (VaultError, DataStoreError, ContentError, LibraryError, SessionError) as error:
        raise _error(error)


@router.put("/api/v1/content/articles/{content_hash}/classification")
async def update_local_classification(content_hash: str, payload: LocalClassificationPayload, request: Request) -> dict:
    try:
        return _with_content(request, lambda connection, identity: set_local_classification(connection, content_hash, payload.category, payload.badges))
    except (VaultError, DataStoreError, ContentError, LibraryError, SessionError) as error:
        raise _error(error)


@router.post("/api/v1/content/drafts")
async def new_draft(payload: DraftPayload, request: Request) -> dict:
    try:
        return _with_content(request, lambda connection, identity: create_draft(connection, identity, payload.content_type, payload.title, payload.body, payload.article_id, payload.previous_hash))
    except (VaultError, DataStoreError, ContentError, SessionError) as error:
        raise _error(error)


@router.get("/api/v1/content/drafts")
async def drafts(request: Request) -> dict:
    try:
        return {"rascunhos": _with_content(request, list_drafts)}
    except (VaultError, DataStoreError, ContentError, SessionError) as error:
        raise _error(error)


@router.put("/api/v1/content/drafts/{draft_id}")
async def edit_draft(draft_id: str, payload: DraftUpdatePayload, request: Request) -> dict[str, str]:
    try:
        _with_content(request, lambda connection, identity: update_draft(connection, identity, draft_id, payload.title, payload.body))
        return {"status": "RASCUNHO_ATUALIZADO"}
    except (VaultError, DataStoreError, ContentError, SessionError) as error:
        raise _error(error)


@router.delete("/api/v1/content/drafts/{draft_id}")
async def remove_draft(draft_id: str, payload: DraftActionPayload, request: Request) -> dict[str, str]:
    try:
        _with_content(request, lambda connection, identity: delete_draft(connection, identity, draft_id))
        return {"status": "RASCUNHO_EXCLUIDO"}
    except (VaultError, DataStoreError, ContentError, SessionError) as error:
        raise _error(error)


@router.post("/api/v1/content/drafts/{draft_id}/review")
async def review(draft_id: str, payload: DraftActionPayload, request: Request) -> dict[str, str]:
    try:
        _with_content(request, lambda connection, identity: review_draft(connection, identity, draft_id))
        return {"status": "EM_REVISAO"}
    except (VaultError, DataStoreError, ContentError, SessionError) as error:
        raise _error(error)


@router.post("/api/v1/content/drafts/{draft_id}/publish")
async def publish(draft_id: str, payload: PublishPayload, request: Request) -> dict:
    try:
        return _with_content(request, lambda connection, identity: publish_draft(connection, identity, draft_id, payload.confirmed))
    except (VaultError, DataStoreError, ContentError, SessionError) as error:
        raise _error(error)


@router.post("/api/v1/content/exports/{mode}")
async def export_content(mode: str, payload: ExportPayload, request: Request) -> dict[str, str]:
    try:
        def write_export(connection, identity):
            session = sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
            artifact = build_export(connection, identity, mode, payload.since, payload.unexported_only)
            save_export_artifact(artifact, session.identity["pseudonym"])
            import cbor2
            header_length = int.from_bytes(artifact[5:9], "big")
            header = cbor2.loads(artifact[9:9 + header_length])
            connection.execute("INSERT INTO export_records(export_id, mode, exported_at) VALUES (?, ?, ?)", (header["exportacao_id"], header["modalidade"], header["emitido_em"]))
            selected = "SELECT p.content_hash FROM publications p WHERE p.publication_status='PUBLICADO'"
            parameters = []
            if payload.since:
                selected += " AND p.created_at >= ?"; parameters.append(payload.since)
            if payload.unexported_only:
                selected += " AND p.content_hash NOT IN (SELECT content_hash FROM export_items)"
            for row in connection.execute(selected, parameters):
                connection.execute("INSERT INTO export_items(export_id, content_hash) VALUES (?, ?)", (header["exportacao_id"], row[0]))
            return {"status": "EXPORTACAO_GERADA"}
        return _with_content(request, write_export)
    except NativeDialogError as error:
        raise HTTPException(409, "A exportação foi cancelada no diálogo local.") from error
    except (VaultError, DataStoreError, ArkxError, SessionError) as error:
        raise _error(error)


@router.post("/api/v1/content/imports")
async def import_content(payload: DraftActionPayload, request: Request) -> dict:
    from backend.native_dialog import collect_export_artifact
    try:
        raw = collect_export_artifact()
        session = sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
        result = _with_content(request, lambda connection, identity: import_items(connection, identity, read_export(connection, raw, identity)))
        if result.get("status") == "COPIA_REVOGADA":
            sessions.destroy(request.cookies.get(SESSION_COOKIE))
        return result
    except NativeDialogError as error:
        raise HTTPException(409, "A importação foi cancelada no diálogo local.") from error
    except ArkxError as error:
        raise HTTPException(400, str(error)) from error
    except (VaultError, DataStoreError, ArkxError, SessionError) as error:
        raise _error(error)


@router.post("/api/v1/content/remove-local")
async def remove_local_content(payload: ContentHashPayload, request: Request) -> dict[str, str]:
    try:
        def remove(connection, identity):
            member_id = identity['public_identity']['member_id']
            row=connection.execute("SELECT role FROM members WHERE member_id=?",(member_id,)).fetchone()
            remove_foreign_content(connection, member_id, row[0] if row else 'MEMBRO', payload.content_hash)
            return {'status':'CONTEUDO_REMOVIDO_LOCALMENTE'}
        return _with_content(request, remove)
    except (VaultError, DataStoreError, LibraryError, SessionError) as error:
        raise _error(error)


@router.post("/api/v1/content/reimport")
async def reimport_content(payload: ContentHashPayload, request: Request) -> dict[str, str]:
    try:
        return _with_content(request, lambda connection, identity: (allow_reimport(connection, payload.content_hash), {'status':'REIMPORTACAO_HABILITADA'})[1])
    except (VaultError, DataStoreError, LibraryError, SessionError) as error:
        raise _error(error)

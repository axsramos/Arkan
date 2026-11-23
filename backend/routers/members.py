"""Rotas locais de administração exclusiva do Guardião."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.member_management import MemberManagementError, administration_snapshot, issue_invitation, revoke_member
from backend.native_dialog import NativeDialogError
from backend.data_store import DataStoreError, open_data_store
from backend.vault import VaultError
from backend.session import SESSION_COOKIE, SessionError, sessions


router = APIRouter()


class GuardianSessionPayload(BaseModel):
    pass


class InvitationPayload(GuardianSessionPayload):
    pseudonym: str = Field(min_length=1, max_length=80)


class IdentifierPayload(GuardianSessionPayload):
    identifier: str = Field(min_length=36, max_length=36)


def _error(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _open_guardian(request: Request):
    from backend.config import STORAGE_DIR
    session = sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
    data_key = session.data_key
    return open_data_store(Path(STORAGE_DIR), data_key), session.identity


def _with_guardian(request: Request, operation):
    connection, identity = _open_guardian(request)
    try:
        result = operation(connection, identity)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _with_guardian_delivery(request: Request, operation, deliver) -> None:
    """Confirma estado e arquivo juntos; cancelar o diálogo reverte a escrita."""
    connection, identity = _open_guardian(request)
    try:
        artifact = operation(connection, identity)
        deliver(artifact)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/v1/members/overview")
async def overview(payload: GuardianSessionPayload, request: Request) -> dict:
    try:
        return _with_guardian(request, administration_snapshot)
    except (VaultError, DataStoreError, MemberManagementError, SessionError):
        raise _error(403, "Ação administrativa não autorizada.")
@router.post("/api/v1/members/invitations")
async def create_invitation(payload: InvitationPayload, request: Request) -> dict[str, str]:
    try:
        from backend.native_dialog import save_invitation_artifact
        _with_guardian_delivery(request, lambda connection, identity: issue_invitation(connection, identity, payload.pseudonym), save_invitation_artifact)
        return {"status": "INGRESSO_EMITIDO"}
    except NativeDialogError as error:
        raise _error(409, "A emissão foi cancelada no diálogo local.") from error
    except (VaultError, DataStoreError, MemberManagementError, SessionError):
        raise _error(403, "Ação administrativa não autorizada.")


__all__ = ["router"]
@router.post("/api/v1/members/revoke")
async def revoke_active_member(payload: IdentifierPayload, request: Request) -> dict[str, str]:
    try:
        _with_guardian(request, lambda connection, identity: revoke_member(connection, identity, payload.identifier))
        return {"status": "MEMBRO_REVOGADO"}
    except NativeDialogError as error:
        raise _error(409, "A revogação foi cancelada no diálogo local.") from error
    except (VaultError, DataStoreError, MemberManagementError, SessionError):
        raise _error(403, "Ação administrativa não autorizada.")

__all__ = ["router"]

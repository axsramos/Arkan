"""Rotas locais que não transportam PIN nem credenciais privadas por HTTP."""
from pathlib import Path
from shutil import disk_usage

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from backend.activation import prepare_activation
from backend.activation_coordinator import confirm_initial_guardian, confirm_joined_member_v2, confirm_recovered_member
from backend.config import STORAGE_DIR, storage_is_activated
from backend.native_dialog import (
    NativeDialogError, collect_invitation_artifact, collect_new_pin, collect_pin,
    collect_recovery_credential, save_recovery_credential,
)
from backend.protocol import ProtocolError, decode_artifact, verify_invitation_v2
from backend.session import IDLE_TIMEOUT_SECONDS, SESSION_COOKIE, SessionError, sessions
from backend.data_store import DataStoreError, open_data_store
from backend.vault import (
    VaultError, create_activation_material, create_invited_member_activation_material, create_recovery_activation_material, write_vault,
    data_key_with_pin, identity_with_data_key, load_vault,
)

router = APIRouter()


class SetupPayload(BaseModel):
    pseudonym: str = Field(min_length=1, max_length=80)


class JoinPayload(BaseModel):
    pseudonym: str = Field(min_length=1, max_length=80)


class RecoverPayload(BaseModel):
    pseudonym: str = Field(min_length=1, max_length=80)


def _error(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _session_summary(identity: dict, data_key: bytes) -> dict[str, str]:
    """Monta somente a apresentação pública da sessão já desbloqueada."""
    public = identity["public_identity"]
    connection = open_data_store(STORAGE_DIR, data_key)
    try:
        row = connection.execute("SELECT role FROM members WHERE member_id = ?", (public["member_id"],)).fetchone()
    finally:
        connection.close()
    return {"pseudonym": identity["pseudonym"], "role": row[0] if row else "MEMBRO"}


def _create_session_from_pin(pin: str) -> tuple[str, dict[str, str]]:
    vault = load_vault(Path(STORAGE_DIR))
    data_key = data_key_with_pin(vault, pin)
    identity = identity_with_data_key(vault, data_key)
    return sessions.create(data_key, identity), _session_summary(identity, data_key)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", secure=False, max_age=IDLE_TIMEOUT_SECONDS, path="/")


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/api/v1/auth/check-setup")
@router.get("/api/v1/node/check-setup")
async def check_setup_status() -> dict[str, bool]:
    return {"is_configured": storage_is_activated(STORAGE_DIR)}


@router.get("/api/v1/auth/session")
async def session_status(request: Request) -> dict[str, str | bool]:
    try:
        session = sessions.get(request.cookies.get(SESSION_COOKIE))
        return {"is_unlocked": True, "pseudonym": session.identity["pseudonym"]}
    except SessionError:
        return {"is_unlocked": False}


@router.get("/api/v1/node/storage")
async def storage_usage(request: Request) -> dict[str, float]:
    """Retorna somente a ocupação percentual do disco da cópia local ativa."""
    try:
        sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
        usage = disk_usage(STORAGE_DIR)
        return {"percentual_usado": round((usage.used / usage.total) * 100, 2) if usage.total else 0}
    except (SessionError, OSError):
        raise _error(status.HTTP_401_UNAUTHORIZED, "Sessão local bloqueada.")


@router.post("/api/v1/auth/setup", status_code=status.HTTP_201_CREATED)
async def setup_first_access(payload: SetupPayload, response: Response) -> dict[str, str]:
    if storage_is_activated(STORAGE_DIR):
        raise _error(status.HTTP_409_CONFLICT, "Esta cópia já possui uma credencial configurada.")
    try:
        pin = collect_new_pin()
        material = create_activation_material(payload.pseudonym, pin)
        save_recovery_credential(material.recovery_artifact)
        confirm_initial_guardian(prepare_activation(STORAGE_DIR), material)
        token, summary = _create_session_from_pin(pin)
        _set_session_cookie(response, token)
        return {"status": "ATIVACAO_CONCLUIDA", **summary}
    except NativeDialogError as error:
        raise _error(status.HTTP_409_CONFLICT, "A ativação foi cancelada no diálogo local.") from error
    except (VaultError, OSError, DataStoreError):
        raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível concluir a ativação local.")


@router.post("/api/v1/auth/join", status_code=status.HTTP_201_CREATED)
async def join_with_invitation(payload: JoinPayload, response: Response) -> dict[str, str]:
    """Ativa membro sem expor PIN ou artefato público ao frontend."""
    if storage_is_activated(STORAGE_DIR):
        raise _error(status.HTTP_409_CONFLICT, "Esta cópia já possui uma credencial configurada.")
    try:
        invitation = decode_artifact(collect_invitation_artifact())
        verify_invitation_v2(invitation)
        if invitation["pseudonimo"].casefold() != payload.pseudonym.strip().casefold():
            raise VaultError("Credencial de acesso inválida.")
        pin = collect_new_pin()
        material = create_invited_member_activation_material(invitation, pin)
        save_recovery_credential(material.recovery_artifact)
        confirm_joined_member_v2(prepare_activation(STORAGE_DIR), material, invitation)
        token, summary = _create_session_from_pin(pin)
        _set_session_cookie(response, token)
        return {"status": "ATIVACAO_CONCLUIDA", **summary}
    except NativeDialogError as error:
        raise _error(status.HTTP_409_CONFLICT, "A ativação foi cancelada no diálogo local.") from error
    except (ProtocolError, VaultError, ValueError):
        raise _error(status.HTTP_400_BAD_REQUEST, "O ingresso não é válido para esta cópia.")
    except (OSError, DataStoreError):
        raise _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível concluir a ativação local.")


@router.post("/api/v1/auth/unlock")
async def unlock_node(response: Response) -> dict[str, str]:
    try:
        token, summary = _create_session_from_pin(collect_pin("Desbloquear Arkan"))
        _set_session_cookie(response, token)
        return {"status": "DESBLOQUEADO", **summary}
    except NativeDialogError as error:
        raise _error(status.HTTP_409_CONFLICT, "O desbloqueio foi cancelado no diálogo local.") from error
    except (VaultError, DataStoreError):
        raise _error(status.HTTP_401_UNAUTHORIZED, "Credencial de acesso incorreta.")


@router.post("/api/v1/auth/recover")
async def recover_node(payload: RecoverPayload, response: Response) -> dict[str, str]:
    try:
        recovery_artifact = collect_recovery_credential()
        new_pin = collect_new_pin()
        material = create_recovery_activation_material(recovery_artifact, payload.pseudonym, new_pin)
        if storage_is_activated(STORAGE_DIR):
            current = load_vault(Path(STORAGE_DIR))
            if current["public_identity"]["member_id"] != material.public_identity["member_id"] or current["public_identity"]["network_id"] != material.public_identity["network_id"]:
                raise VaultError("Credencial de acesso inválida.")
            write_vault(Path(STORAGE_DIR), material.vault)
        else:
            confirm_recovered_member(prepare_activation(STORAGE_DIR), material)
        token, summary = _create_session_from_pin(new_pin)
        _set_session_cookie(response, token)
        return {"status": "RECUPERADO", **summary}
    except NativeDialogError as error:
        raise _error(status.HTTP_409_CONFLICT, "A recuperação foi cancelada no diálogo local.") from error
    except VaultError:
        raise _error(status.HTTP_401_UNAUTHORIZED, "Credencial de acesso incorreta.")


@router.post("/api/v1/application/exit", status_code=status.HTTP_202_ACCEPTED)
async def exit_application(request: Request) -> dict[str, str]:
    """Encerra somente a cópia local após confirmar uma sessão ainda ativa."""
    try:
        sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
    except SessionError as error:
        raise _error(status.HTTP_401_UNAUTHORIZED, "Sessão local bloqueada.") from error
    request_shutdown = getattr(request.app.state, "request_shutdown", None)
    if not callable(request_shutdown):
        raise _error(status.HTTP_503_SERVICE_UNAVAILABLE, "O encerramento local não está disponível.")
    request_shutdown()
    return {"status": "ENCERRANDO"}


@router.post("/api/v1/auth/activity")
async def renew_activity(request: Request) -> dict[str, str]:
    try:
        sessions.get(request.cookies.get(SESSION_COOKIE), renew=True)
        return {"status": "ATIVA"}
    except SessionError as error:
        raise _error(status.HTTP_401_UNAUTHORIZED, "Sessão local bloqueada.") from error


__all__ = ["router"]

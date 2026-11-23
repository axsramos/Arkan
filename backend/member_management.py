"""Administração local e assinada de membros com `ARKA v2` e `ARKI v2`."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from backend.database import migrate_member_management_schema
from backend.protocol import (
    ProtocolError,
    artifact_hash,
    decode_artifact,
    sign_authorization_v2,
    sign_invitation_v2,
    encode_artifact_v2,
)
from backend.vault import create_member_identity


class MemberManagementError(RuntimeError):
    """Falha não sensível na administração local de membros."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_state(connection: Any, network_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT state_artifact FROM authorization_states WHERE network_id = ? ORDER BY sequence_number DESC LIMIT 1",
        (network_id,),
    ).fetchone()
    return decode_artifact(row[0]) if row else None


def _guardian_context(connection: Any, identity: dict[str, Any]) -> tuple[str, str, bytes, dict[str, Any] | None]:
    public = identity["public_identity"]
    row = connection.execute(
        """SELECT n.network_id, n.guardian_member_id, m.status
           FROM networks n JOIN members m ON m.member_id = n.guardian_member_id
           WHERE n.network_id = ?""",
        (public["network_id"],),
    ).fetchone()
    if row is None or row[1] != public["member_id"] or row[2] != "ATIVO":
        raise MemberManagementError("Ação permitida somente ao Guardião ativo.")
    try:
        signing_key = base64.b64decode(identity["signing_private_key"], validate=True)
        guardian_key = base64.b64decode(public["signing_public_key"], validate=True)
    except (KeyError, ValueError, TypeError) as error:
        raise MemberManagementError("Não foi possível autorizar a administração local.") from error
    return row[0], row[1], signing_key, _load_state(connection, row[0])


def _initial_state(connection: Any, identity: dict[str, Any]) -> dict[str, Any]:
    public = identity["public_identity"]
    now = _timestamp()
    return {
        "tipo": "ARKA", "versao": 2, "rede_id": public["network_id"],
        "guardiao_id": public["member_id"],
        "guardiao_chave_assinatura": base64.b64decode(public["signing_public_key"], validate=True),
        "sequencia": 1, "anterior_hash": None, "emitido_em": now,
        "membros": [{
            "membro_id": public["member_id"], "pseudonimo": identity["pseudonym"], "papel": "GUARDIAO", "status": "ATIVO",
            "chave_assinatura": base64.b64decode(public["signing_public_key"], validate=True),
            "chave_cifragem": base64.b64decode(public["encryption_public_key"], validate=True),
            "ativacao_hash": base64.b64decode(public["activation_hash"], validate=True),
            "efetivo_em": public["created_at"], "revogado_em": None,
        }], "assinatura": b"",
    }


def _next_state(current: dict[str, Any] | None, connection: Any, identity: dict[str, Any]) -> dict[str, Any]:
    if current is None:
        return _initial_state(connection, identity)
    return {
        **current,
        "sequencia": current["sequencia"] + 1,
        "anterior_hash": artifact_hash(current),
        "emitido_em": _timestamp(),
        "membros": [dict(member) for member in current["membros"]],
        "assinatura": b"",
    }


def _store_state(connection: Any, state: dict[str, Any], signing_key: bytes) -> dict[str, Any]:
    signed = sign_authorization_v2(state, signing_key)
    artifact = encode_artifact_v2(signed)
    connection.execute(
        "INSERT INTO authorization_states(network_id, sequence_number, state_hash, state_artifact, created_at) VALUES (?, ?, ?, ?, ?)",
        (signed["rede_id"], signed["sequencia"], artifact_hash(signed), artifact, signed["emitido_em"]),
    )
    return signed


def ensure_member_management_migration(connection: Any, storage_version: int) -> int:
    """Aplica a única migração local prevista para o histórico `ARKA`."""
    if storage_version < 2:
        migrate_member_management_schema(connection)
        return 2
    return storage_version


def issue_invitation(connection: Any, identity: dict[str, Any], pseudonym: str) -> bytes:
    """Cria Membro ativo e produz `ARKI v2` para entrega manual imediata."""
    network_id, guardian_id, signing_key, current = _guardian_context(connection, identity)
    state = _next_state(current, connection, identity)
    now = _timestamp()
    expires = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
    if not isinstance(pseudonym, str) or not 1 <= len(pseudonym.strip()) <= 80:
        raise MemberManagementError("Pseudônimo inválido.")
    member_id, copy_id, invitation_id = str(uuid4()), str(uuid4()), str(uuid4())
    member_identity = create_member_identity()
    activation_hash = hashlib.sha256(f"{copy_id}:{member_id}".encode("utf-8")).digest()
    state["membros"].append({
        "membro_id": member_id, "pseudonimo": pseudonym.strip(), "papel": "MEMBRO", "status": "ATIVO",
        "chave_assinatura": base64.b64decode(member_identity.public_identity["signing_public_key"]),
        "chave_cifragem": base64.b64decode(member_identity.public_identity["encryption_public_key"]),
        "ativacao_hash": activation_hash, "efetivo_em": now, "revogado_em": None,
    })
    signed_state = _store_state(connection, state, signing_key)
    connection.execute(
        "INSERT INTO members(member_id, network_id, signing_public_key, encryption_public_key, role, status, activation_hash, created_at) VALUES (?, ?, ?, ?, 'MEMBRO', 'ATIVO', ?, ?)",
        (member_id, network_id, member_identity.public_identity["signing_public_key"], member_identity.public_identity["encryption_public_key"], base64.b64encode(activation_hash).decode(), now),
    )
    invitation = {
        "tipo": "ARKI", "versao": 2, "rede_id": network_id, "ingresso_id": invitation_id,
        "membro_id": member_id, "guardiao_id": guardian_id, "copia_id": copy_id, "pseudonimo": pseudonym.strip(),
        "arka_hash": artifact_hash(signed_state), "emitido_em": now, "expira_em": expires, "arka": signed_state,
        "identidade": {"chave_assinatura_privada": member_identity.signing_private_key, "chave_cifragem_privada": member_identity.encryption_private_key},
        "assinatura": b"",
    }
    return encode_artifact_v2(sign_invitation_v2(invitation, signing_key))


def revoke_member(connection: Any, identity: dict[str, Any], member_id: str) -> bytes:
    """Revoga membro sem apagar conteúdo publicado anteriormente."""
    network_id, guardian_id, signing_key, current = _guardian_context(connection, identity)
    if current is None or member_id == guardian_id:
        raise MemberManagementError("Membro indisponível para revogação.")
    state = _next_state(current, connection, identity)
    matches = [item for item in state["membros"] if item["membro_id"] == member_id and item["status"] == "ATIVO"]
    if len(matches) != 1:
        raise MemberManagementError("Membro indisponível para revogação.")
    matches[0].update({"status": "REVOGADO", "revogado_em": _timestamp()})
    connection.execute("UPDATE members SET status = 'REVOGADO' WHERE member_id = ? AND network_id = ?", (member_id, network_id))
    signed = _store_state(connection, state, signing_key)
    return encode_artifact_v2(signed)


def administration_snapshot(connection: Any, identity: dict[str, Any]) -> dict[str, Any]:
    """Retorna somente estados públicos para a tela local do Guardião."""
    _, _, _, current = _guardian_context(connection, identity)
    if current is None:
        return {"membros": []}
    return {"membros": [{key: value for key, value in item.items() if key not in {"chave_assinatura", "chave_cifragem", "ativacao_hash"}} for item in current["membros"]]}

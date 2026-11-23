"""Codificação canônica e validação dos formatos públicos v2."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import cbor2
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


MAX_ARTIFACT_SIZE = 256 * 1024
MAX_DEPTH = 16
SIGNATURE_LENGTH = 64
PUBLIC_KEY_LENGTH = 32
HASH_LENGTH = 32


class ProtocolError(ValueError):
    """Artefato de protocolo inválido, sem detalhar dados internos."""


MEMBER_FIELDS = {"membro_id", "pseudonimo", "papel", "status", "chave_assinatura", "chave_cifragem", "ativacao_hash", "efetivo_em", "revogado_em"}


def _depth(value: Any, current: int = 0) -> int:
    if current > MAX_DEPTH:
        raise ProtocolError("Artefato de protocolo inválido.")
    if isinstance(value, dict):
        return max((_depth(item, current + 1) for item in value.values()), default=current)
    if isinstance(value, (list, tuple)):
        return max((_depth(item, current + 1) for item in value), default=current)
    return current


def _uuid(value: Any) -> None:
    if not isinstance(value, str):
        raise ProtocolError("Identificador de protocolo inválido.")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise ProtocolError("Identificador de protocolo inválido.") from error
    if str(parsed) != value:
        raise ProtocolError("Identificador de protocolo inválido.")


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtocolError("Data de protocolo inválida.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ProtocolError("Data de protocolo inválida.") from error
    if parsed.tzinfo != timezone.utc or parsed.isoformat().replace("+00:00", "Z") != value:
        raise ProtocolError("Data de protocolo inválida.")
    return parsed


def _bytes(value: Any, length: int) -> None:
    if not isinstance(value, bytes) or len(value) != length:
        raise ProtocolError("Campo binário de protocolo inválido.")


def _pseudonym(value: Any) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= 80 or value != value.strip() or any(ord(character) < 32 for character in value):
        raise ProtocolError("Pseudônimo de protocolo inválido.")


def decode_artifact(raw: bytes) -> dict[str, Any]:
    """Decodifica somente CBOR determinístico, limitado e sem ambiguidade."""
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_ARTIFACT_SIZE:
        raise ProtocolError("Artefato de protocolo inválido.")
    try:
        artifact = cbor2.loads(raw)
    except Exception as error:
        raise ProtocolError("Artefato de protocolo inválido.") from error
    if not isinstance(artifact, dict):
        raise ProtocolError("Artefato de protocolo inválido.")
    _depth(artifact)
    try:
        if cbor2.dumps(artifact, canonical=True) != raw:
            raise ProtocolError("Codificação de protocolo não canônica.")
    except cbor2.CBOREncodeError as error:
        raise ProtocolError("Artefato de protocolo inválido.") from error
    return artifact


def canonical_without_signature(artifact: dict[str, Any]) -> bytes:
    if not isinstance(artifact, dict) or "assinatura" not in artifact:
        raise ProtocolError("Formato de protocolo inválido.")
    try:
        encoded = cbor2.dumps({key: value for key, value in artifact.items() if key != "assinatura"}, canonical=True)
    except cbor2.CBOREncodeError as error:
        raise ProtocolError("Formato de protocolo inválido.") from error
    if len(encoded) > MAX_ARTIFACT_SIZE:
        raise ProtocolError("Artefato excede o limite permitido.")
    return encoded


def artifact_hash(artifact: dict[str, Any]) -> bytes:
    return hashlib.sha256(canonical_without_signature(artifact)).digest()


def verify_signature(artifact: dict[str, Any], public_key: bytes) -> None:
    _bytes(public_key, PUBLIC_KEY_LENGTH)
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(artifact["assinatura"], canonical_without_signature(artifact))
    except Exception as error:
        raise ProtocolError("Assinatura de protocolo inválida.") from error


def _validate_member(member: Any, guardian_id: str, guardian_key: bytes) -> None:
    if not isinstance(member, dict) or set(member) != MEMBER_FIELDS:
        raise ProtocolError("Membro de protocolo inválido.")
    _uuid(member["membro_id"])
    _pseudonym(member["pseudonimo"])
    if member["papel"] not in {"GUARDIAO", "MEMBRO"} or member["status"] not in {"ATIVO", "REVOGADO"}:
        raise ProtocolError("Membro de protocolo inválido.")
    _bytes(member["chave_assinatura"], PUBLIC_KEY_LENGTH)
    _bytes(member["chave_cifragem"], PUBLIC_KEY_LENGTH)
    _bytes(member["ativacao_hash"], HASH_LENGTH)
    _timestamp(member["efetivo_em"])
    if member["status"] == "ATIVO" and member["revogado_em"] is not None:
        raise ProtocolError("Membro de protocolo inválido.")
    if member["status"] == "REVOGADO":
        _timestamp(member["revogado_em"])
    if member["membro_id"] == guardian_id and (member["papel"] != "GUARDIAO" or member["chave_assinatura"] != guardian_key):
        raise ProtocolError("Guardião de protocolo inválido.")


ARKI_V2_FIELDS = {
    "tipo", "versao", "rede_id", "ingresso_id", "membro_id", "guardiao_id", "copia_id",
    "pseudonimo", "emitido_em", "expira_em", "arka_hash", "arka", "identidade", "assinatura",
}
ARKI_V2_IDENTITY_FIELDS = {"chave_assinatura_privada", "chave_cifragem_privada"}


def _validate_authorization_v2(authorization: dict[str, Any]) -> None:
    required = {"tipo", "versao", "rede_id", "guardiao_id", "guardiao_chave_assinatura", "sequencia", "anterior_hash", "emitido_em", "membros", "assinatura"}
    if not isinstance(authorization, dict) or set(authorization) != required or authorization.get("tipo") != "ARKA" or authorization.get("versao") != 2:
        raise ProtocolError("Formato de protocolo inválido.")
    for name in ("rede_id", "guardiao_id"):
        _uuid(authorization[name])
    _bytes(authorization["guardiao_chave_assinatura"], PUBLIC_KEY_LENGTH)
    if not isinstance(authorization["sequencia"], int) or authorization["sequencia"] < 1:
        raise ProtocolError("Sequência de autorização inválida.")
    if authorization["sequencia"] == 1:
        if authorization["anterior_hash"] is not None:
            raise ProtocolError("Encadeamento de autorização inválido.")
    else:
        _bytes(authorization["anterior_hash"], HASH_LENGTH)
    _timestamp(authorization["emitido_em"])
    if not isinstance(authorization["membros"], list):
        raise ProtocolError("Coleção de autorização inválida.")
    member_ids: set[str] = set()
    for member in authorization["membros"]:
        _validate_member(member, authorization["guardiao_id"], authorization["guardiao_chave_assinatura"])
        if member["membro_id"] in member_ids:
            raise ProtocolError("Membro duplicado no estado de autorização.")
        member_ids.add(member["membro_id"])
    if authorization["guardiao_id"] not in member_ids:
        raise ProtocolError("Guardião ausente no estado de autorização.")
    verify_signature(authorization, authorization["guardiao_chave_assinatura"])


def validate_authorization_v2(authorization: dict[str, Any]) -> None:
    """Valida o instantâneo de autorização distribuído pelo `ARKX v2`."""
    _validate_authorization_v2(authorization)


def verify_invitation_v2(invitation: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Valida convite imediato, já autorizado e portador da identidade do Membro."""
    if not isinstance(invitation, dict) or set(invitation) != ARKI_V2_FIELDS or invitation.get("tipo") != "ARKI" or invitation.get("versao") != 2:
        raise ProtocolError("Formato de protocolo inválido.")
    for name in ("rede_id", "ingresso_id", "membro_id", "guardiao_id", "copia_id"):
        _uuid(invitation[name])
    _pseudonym(invitation["pseudonimo"])
    issued, expires = _timestamp(invitation["emitido_em"]), _timestamp(invitation["expira_em"])
    if expires < issued or expires - issued > timedelta(days=7):
        raise ProtocolError("Validade de ingresso inválida.")
    _bytes(invitation["arka_hash"], HASH_LENGTH)
    authorization = invitation["arka"]
    _validate_authorization_v2(authorization)
    if invitation["arka_hash"] != artifact_hash(authorization) or invitation["rede_id"] != authorization["rede_id"] or invitation["guardiao_id"] != authorization["guardiao_id"]:
        raise ProtocolError("Estado de autorização incompatível.")
    identity = invitation["identidade"]
    if not isinstance(identity, dict) or set(identity) != ARKI_V2_IDENTITY_FIELDS:
        raise ProtocolError("Identidade de ingresso inválida.")
    signing_private, encryption_private = identity["chave_assinatura_privada"], identity["chave_cifragem_privada"]
    _bytes(signing_private, 32)
    _bytes(encryption_private, 32)
    signing_public = Ed25519PrivateKey.from_private_bytes(signing_private).public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    encryption_public = X25519PrivateKey.from_private_bytes(encryption_private).public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    member = next((item for item in authorization["membros"] if item["membro_id"] == invitation["membro_id"]), None)
    if member is None or member["status"] != "ATIVO" or member["pseudonimo"] != invitation["pseudonimo"] or member["chave_assinatura"] != signing_public or member["chave_cifragem"] != encryption_public:
        raise ProtocolError("Ingresso incompatível.")
    verify_signature(invitation, authorization["guardiao_chave_assinatura"])
    if (now or datetime.now(timezone.utc)) > expires:
        raise ProtocolError("Ingresso vencido.")
    return member


def sign_authorization_v2(authorization: dict[str, Any], signing_key: bytes) -> dict[str, Any]:
    unsigned = {**authorization, "assinatura": b"\x00" * SIGNATURE_LENGTH}
    try:
        signature = Ed25519PrivateKey.from_private_bytes(signing_key).sign(canonical_without_signature(unsigned))
    except Exception as error:
        raise ProtocolError("Não foi possível assinar a autorização.") from error
    signed = {**authorization, "assinatura": signature}
    _validate_authorization_v2(signed)
    return signed


def sign_invitation_v2(invitation: dict[str, Any], signing_key: bytes) -> dict[str, Any]:
    unsigned = {**invitation, "assinatura": b"\x00" * SIGNATURE_LENGTH}
    try:
        signature = Ed25519PrivateKey.from_private_bytes(signing_key).sign(canonical_without_signature(unsigned))
    except Exception as error:
        raise ProtocolError("Não foi possível assinar o ingresso.") from error
    signed = {**invitation, "assinatura": signature}
    verify_invitation_v2(signed)
    return signed


def encode_artifact_v2(artifact: dict[str, Any]) -> bytes:
    if artifact.get("tipo") == "ARKA":
        _validate_authorization_v2(artifact)
    elif artifact.get("tipo") == "ARKI":
        verify_invitation_v2(artifact)
    else:
        raise ProtocolError("Formato de protocolo inválido.")
    return cbor2.dumps(artifact, canonical=True)

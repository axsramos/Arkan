"""Cofre local versionado e credencial portátil por posse do membro."""

import base64
import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path

from argon2.low_level import Type, hash_secret_raw
from argon2.exceptions import HashingError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import cbor2


VAULT_VERSION = 3
ARGON2_PARAMETERS = {"time_cost": 3, "memory_cost": 65536, "parallelism": 1, "hash_len": 32}
PIN_INFO = b"arkan/v1/pin-envelope"
PAYLOAD_INFO = b"arkan/v2/vault-payload"
RECOVERY_MAX_SIZE = 16 * 1024


class VaultError(RuntimeError):
    """Falha não sensível de abertura ou validação do cofre."""


@dataclass(frozen=True)
class ActivationMaterial:
    """Material transitório destinado exclusivamente ao coordenador local."""

    data_key: bytes
    vault: dict[str, Any]
    public_identity: dict[str, str]
    signing_private_key: bytes
    recovery_artifact: bytes
    recovery_authorization: dict[str, Any] | None = None
    recovery_invitation_id: str | None = None


@dataclass(frozen=True)
class MemberIdentityMaterial:
    """Identidade destinada ao convite, mantida pelo Guardião e pelo arquivo entregue."""

    signing_private_key: bytes
    encryption_private_key: bytes
    public_identity: dict[str, str]


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _unb64(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (TypeError, ValueError) as error:
        raise VaultError("Não foi possível abrir o cofre local.") from error


def _pin_key(pin: str, salt: bytes) -> bytes:
    if not isinstance(pin, str) or not pin.isdigit() or not 4 <= len(pin) <= 6:
        raise VaultError("Credencial de acesso inválida.")
    try:
        return hash_secret_raw(pin.encode("utf-8"), salt, type=Type.ID, **ARGON2_PARAMETERS)
    except HashingError as error:
        raise VaultError("Não foi possível abrir o cofre local.") from error


def _encrypt(key: bytes, plaintext: bytes, associated_data: bytes) -> dict[str, str]:
    nonce = os.urandom(12)
    return {"nonce": _b64(nonce), "ciphertext": _b64(AESGCM(key).encrypt(nonce, plaintext, associated_data))}


def _decrypt(key: bytes, envelope: dict[str, str], associated_data: bytes) -> bytes:
    try:
        return AESGCM(key).decrypt(_unb64(envelope["nonce"]), _unb64(envelope["ciphertext"]), associated_data)
    except Exception as error:
        raise VaultError("Credencial de acesso inválida.") from error


def _public_identity(signing_private: bytes, encryption_private: bytes) -> dict[str, str]:
    """Deriva apenas as chaves públicas de uma identidade privada já existente."""
    signing_public = Ed25519PrivateKey.from_private_bytes(signing_private).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    encryption_public = X25519PrivateKey.from_private_bytes(encryption_private).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return {
        "signing_public_key": _b64(signing_public),
        "encryption_public_key": _b64(encryption_public),
    }


def create_member_identity() -> MemberIdentityMaterial:
    """Gera a identidade que o Guardião entrega ao novo Membro no `ARKI v2`."""
    signing_private = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    encryption_private = X25519PrivateKey.generate().private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    return MemberIdentityMaterial(signing_private, encryption_private, _public_identity(signing_private, encryption_private))


def _pseudonym_hash(pseudonym: str) -> bytes:
    if not isinstance(pseudonym, str) or not 1 <= len(pseudonym.strip()) <= 80:
        raise VaultError("Dados de ativação inválidos.")
    return hashlib.sha256(pseudonym.strip().casefold().encode("utf-8")).digest()


def _sign_recovery(unsigned: dict[str, Any], signing_private: bytes) -> bytes:
    try:
        return Ed25519PrivateKey.from_private_bytes(signing_private).sign(cbor2.dumps(unsigned, canonical=True))
    except Exception as error:
        raise VaultError("Não foi possível preparar a credencial portátil.") from error


def _create_recovery_artifact(
    pseudonym: str, network_id: str, member_id: str, copy_id: str, signing_private: bytes, encryption_private: bytes,
    data_key: bytes, authorization: dict[str, Any] | None = None, invitation_id: str | None = None,
) -> bytes:
    unsigned = {
        "tipo": "ARKR",
        "versao": 2,
        "rede_id": network_id,
        "membro_id": member_id,
        "copia_id": copy_id,
        "pseudonimo_hash": _pseudonym_hash(pseudonym),
        "chave_assinatura_privada": signing_private,
        "chave_cifragem_privada": encryption_private,
        "chave_dados": data_key,
    }
    if authorization is not None and invitation_id is not None:
        unsigned["autorizacao"] = authorization
        unsigned["ingresso_id"] = invitation_id
    artifact = {**unsigned, "assinatura": _sign_recovery(unsigned, signing_private)}
    try:
        encoded = cbor2.dumps(artifact, canonical=True)
    except cbor2.CBOREncodeError as error:
        raise VaultError("Não foi possível preparar a credencial portátil.") from error
    if len(encoded) > RECOVERY_MAX_SIZE:
        raise VaultError("Não foi possível preparar a credencial portátil.")
    return encoded


def _create_activation_material(
    pseudonym: str, pin: str, network_id: str, member_id: str, copy_id: str,
    signing_private: bytes | None = None, encryption_private: bytes | None = None,
    recovery_authorization: dict[str, Any] | None = None, recovery_invitation_id: str | None = None, data_key: bytes | None = None,
) -> ActivationMaterial:
    """Gera material de ativação em memória para uma identidade já identificada."""
    if not isinstance(pseudonym, str) or not 1 <= len(pseudonym.strip()) <= 80:
        raise VaultError("Dados de ativação inválidos.")
    generated = create_member_identity() if signing_private is None or encryption_private is None else None
    signing_private = signing_private or generated.signing_private_key
    encryption_private = encryption_private or generated.encryption_private_key
    public = _public_identity(signing_private, encryption_private)
    data_key = data_key or os.urandom(32)
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    activation_hash = _b64(hashlib.sha256(f"{copy_id}:{member_id}".encode("utf-8")).digest())
    payload = {
        "pseudonym": pseudonym.strip(),
        "installation_id": copy_id,
        "member_id": member_id,
        "signing_private_key": _b64(signing_private),
        "encryption_private_key": _b64(encryption_private),
    }
    pin_salt = os.urandom(16)
    vault = {
        "version": VAULT_VERSION,
        "public_identity": {
            **public,
            "network_id": network_id,
            "installation_id": copy_id,
            "member_id": member_id,
            "activation_hash": activation_hash,
            "created_at": created_at,
        },
        "pin": {"salt": _b64(pin_salt), "envelope": _encrypt(_pin_key(pin, pin_salt), data_key, PIN_INFO)},
        "payload": _encrypt(data_key, json.dumps(payload, sort_keys=True).encode("utf-8"), PAYLOAD_INFO),
    }
    return ActivationMaterial(
        data_key=data_key,
        vault=vault,
        public_identity=vault["public_identity"],
        signing_private_key=signing_private,
        recovery_artifact=_create_recovery_artifact(
            pseudonym, network_id, member_id, copy_id, signing_private, encryption_private,
            data_key, recovery_authorization, recovery_invitation_id,
        ),
        recovery_authorization=recovery_authorization,
        recovery_invitation_id=recovery_invitation_id,
    )


def create_activation_material(pseudonym: str, pin: str) -> ActivationMaterial:
    """Gera uma identidade nova de Guardião e todos os envelopes em memória."""
    return _create_activation_material(pseudonym, pin, str(uuid4()), str(uuid4()), str(uuid4()))


def create_member_activation_material(
    pseudonym: str, pin: str, network_id: str, member_id: str, copy_id: str
) -> ActivationMaterial:
    """Gera a identidade local do membro destinada ao ingresso já validado."""
    return _create_activation_material(pseudonym, pin, network_id, member_id, copy_id)


def create_invited_member_activation_material(invitation: dict[str, Any], pin: str) -> ActivationMaterial:
    """Monta o cofre do destinatário a partir da identidade contida no `ARKI v2`."""
    try:
        identity = invitation["identidade"]
        return _create_activation_material(
            invitation["pseudonimo"], pin, invitation["rede_id"], invitation["membro_id"], invitation["copia_id"],
            identity["chave_assinatura_privada"], identity["chave_cifragem_privada"],
            invitation["arka"], invitation["ingresso_id"],
        )
    except (KeyError, TypeError, VaultError) as error:
        raise VaultError("Credencial de acesso inválida.") from error


def write_vault(directory: Path, vault: dict[str, Any]) -> None:
    """Grava a estrutura já cifrada somente no diretório temporário da ativação."""
    temporary_path = directory / "vault.json.tmp"
    temporary_path.write_text(json.dumps(vault, sort_keys=True), encoding="utf-8")
    os.replace(temporary_path, directory / "vault.json")


def load_vault(directory: Path) -> dict[str, Any]:
    """Lê apenas a estrutura cifrada já confirmada no armazenamento local."""
    try:
        vault = json.loads((directory / "vault.json").read_text(encoding="utf-8"))
        if vault.get("version") != VAULT_VERSION:
            raise ValueError("versão incompatível")
        return vault
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise VaultError("Não foi possível abrir o cofre local.") from error


def open_with_pin(vault: dict[str, Any], pin: str) -> None:
    """Valida o PIN e a integridade do cofre sem devolver material secreto."""
    try:
        pin_record = vault["pin"]
        data_key = _decrypt(_pin_key(pin, _unb64(pin_record["salt"])), pin_record["envelope"], PIN_INFO)
        _decrypt(data_key, vault["payload"], PAYLOAD_INFO)
    except (KeyError, TypeError, VaultError) as error:
        raise VaultError("Credencial de acesso inválida.") from error


def data_key_with_pin(vault: dict[str, Any], pin: str) -> bytes:
    """Abre a chave de dados apenas para uma operação local já autorizada por PIN."""
    try:
        pin_record = vault["pin"]
        data_key = _decrypt(_pin_key(pin, _unb64(pin_record["salt"])), pin_record["envelope"], PIN_INFO)
        _decrypt(data_key, vault["payload"], PAYLOAD_INFO)
        return data_key
    except (KeyError, TypeError, VaultError) as error:
        raise VaultError("Credencial de acesso inválida.") from error


def identity_with_pin(vault: dict[str, Any], pin: str) -> dict[str, Any]:
    """Abre a identidade somente no backend para uma ação local autorizada."""
    return identity_with_data_key(vault, data_key_with_pin(vault, pin))


def identity_with_data_key(vault: dict[str, Any], data_key: bytes) -> dict[str, Any]:
    """Abre a identidade com a chave já validada, sem repetir a derivação do PIN."""
    try:
        if not isinstance(data_key, bytes) or len(data_key) != 32:
            raise ValueError("chave inválida")
        payload = json.loads(_decrypt(data_key, vault["payload"], PAYLOAD_INFO).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("carga inválida")
        return {"public_identity": vault["public_identity"], **payload}
    except (KeyError, TypeError, ValueError, SyntaxError, UnicodeDecodeError, VaultError) as error:
        raise VaultError("Credencial de acesso inválida.") from error


def create_recovery_activation_material(raw: bytes, pseudonym: str, pin: str) -> ActivationMaterial:
    """Restaura a identidade de um `ARKR v2` em uma nova cópia local."""
    try:
        if not isinstance(raw, bytes) or not raw or len(raw) > RECOVERY_MAX_SIZE:
            raise ValueError("tamanho")
        artifact = cbor2.loads(raw)
        if not isinstance(artifact, dict) or cbor2.dumps(artifact, canonical=True) != raw:
            raise ValueError("formato")
        required = {
            "tipo", "versao", "rede_id", "membro_id", "copia_id", "pseudonimo_hash",
            "chave_assinatura_privada", "chave_cifragem_privada", "chave_dados", "assinatura",
        }
        member_required = required | {"autorizacao", "ingresso_id"}
        if frozenset(artifact) not in {frozenset(required), frozenset(member_required)} or artifact["tipo"] != "ARKR" or artifact["versao"] != 2:
            raise ValueError("campos")
        if artifact["pseudonimo_hash"] != _pseudonym_hash(pseudonym):
            raise ValueError("pseudonimo")
        signing_private = artifact["chave_assinatura_privada"]
        encryption_private = artifact["chave_cifragem_privada"]
        data_key = artifact["chave_dados"]
        if not isinstance(signing_private, bytes) or len(signing_private) != 32 or not isinstance(encryption_private, bytes) or len(encryption_private) != 32 or not isinstance(data_key, bytes) or len(data_key) != 32:
            raise ValueError("chaves")
        unsigned = {key: value for key, value in artifact.items() if key != "assinatura"}
        public = _public_identity(signing_private, encryption_private)
        Ed25519PublicKey.from_public_bytes(_unb64(public["signing_public_key"])).verify(
            artifact["assinatura"], cbor2.dumps(unsigned, canonical=True)
        )
        authorization = artifact.get("autorizacao")
        invitation_id = artifact.get("ingresso_id")
        if authorization is not None:
            from backend.protocol import validate_authorization_v2

            validate_authorization_v2(authorization)
            member = next((item for item in authorization["membros"] if item["membro_id"] == artifact["membro_id"]), None)
            if (
                not isinstance(invitation_id, str)
                or member is None
                or authorization["rede_id"] != artifact["rede_id"]
                or member["chave_assinatura"] != _unb64(public["signing_public_key"])
                or member["chave_cifragem"] != _unb64(public["encryption_public_key"])
            ):
                raise ValueError("autorizacao")
        return _create_activation_material(
            pseudonym, pin, artifact["rede_id"], artifact["membro_id"], artifact["copia_id"],
            signing_private, encryption_private,
            authorization, invitation_id, data_key,
        )
    except (KeyError, TypeError, ValueError, cbor2.CBORDecodeError, VaultError) as error:
        raise VaultError("Credencial de acesso inválida.") from error

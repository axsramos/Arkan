"""Fábrica SQLCipher versionada para os dados locais em `data/`."""

import hashlib
import json
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from sqlcipher3 import dbapi2 as sqlcipher

from backend.activation import ActivationPreparation, ActivationStateError

FORMAT_VERSION = 11
DATABASE_NAME = "arkan_vault.db"
MANIFEST_NAME = "manifest.json"


class DataStoreError(RuntimeError):
    """Falha não sensível no armazenamento local protegido."""


def _validate_key(data_key: bytes) -> None:
    if not isinstance(data_key, bytes) or len(data_key) != 32:
        raise DataStoreError("Não foi possível abrir os dados locais.")


def _connect(database_path: Path, data_key: bytes):
    _validate_key(data_key)
    connection = sqlcipher.connect(database_path)
    try:
        connection.execute("PRAGMA key = \"x'" + data_key.hex() + "'\"")
        # SQLCipher para Windows pode encerrar o processo por estouro de pilha
        # quando VirtualLock falha com esta proteção ativada. A base continua
        # cifrada e autenticada; somente esse bloqueio de páginas é omitido.
        if sys.platform != "win32":
            connection.execute("PRAGMA cipher_memory_security = ON")
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
        return connection
    except Exception as error:
        connection.close()
        raise DataStoreError("Não foi possível abrir os dados locais.") from error


def _manifest() -> dict[str, Any]:
    return {"format_version": FORMAT_VERSION, "database": DATABASE_NAME, "cipher": "SQLCipher"}


def _write_manifest(directory: Path, manifest: dict[str, Any]) -> None:
    temporary_path = directory / f"{MANIFEST_NAME}.tmp"
    temporary_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    os.replace(temporary_path, directory / MANIFEST_NAME)


def _read_manifest(directory: Path) -> dict[str, Any]:
    try:
        manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("database") != DATABASE_NAME or not isinstance(manifest.get("format_version"), int):
            raise ValueError("manifesto incompatível")
        return manifest
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise DataStoreError("Não foi possível abrir os dados locais.") from error


def create_data_store(preparation: ActivationPreparation, data_key: bytes, initialize: Callable[[Path, Any], None] | None = None) -> None:
    _validate_key(data_key)
    target = preparation.storage_dir
    if target.exists():
        raise ActivationStateError("Esta cópia já possui dados locais.")
    temporary_directory = Path(mkdtemp(prefix=f".{target.name}.activating-", dir=target.parent))
    try:
        connection = _connect(temporary_directory / DATABASE_NAME, data_key)
        try:
            from backend.database import initialize_schema
            initialize_schema(connection)
            if initialize is not None:
                initialize(temporary_directory, connection)
                connection.commit()
        finally:
            connection.close()
        _write_manifest(temporary_directory, _manifest())
        os.replace(temporary_directory, target)
    except Exception:
        if temporary_directory.exists(): shutil.rmtree(temporary_directory)
        raise


def open_data_store(data_dir: Path | str, data_key: bytes):
    directory = Path(data_dir)
    manifest = _read_manifest(directory)
    if not 1 <= manifest["format_version"] <= FORMAT_VERSION:
        raise DataStoreError("Os dados locais exigem migração.")
    return _connect(directory / DATABASE_NAME, data_key)


def migrate_data_store(data_dir: Path | str, data_key: bytes, target_version: int, migration: Callable[[Any], None]) -> Path:
    directory = Path(data_dir); manifest = _read_manifest(directory); source_version = manifest["format_version"]
    if target_version <= source_version: raise DataStoreError("A versão de migração é inválida.")
    database_path = directory / DATABASE_NAME; backup_path = directory / f"{DATABASE_NAME}.backup-v{source_version}"
    if backup_path.exists(): raise DataStoreError("Já existe uma cópia recuperável pendente.")
    shutil.copy2(database_path, backup_path)
    if hashlib.sha256(database_path.read_bytes()).digest() != hashlib.sha256(backup_path.read_bytes()).digest(): raise DataStoreError("Não foi possível preservar uma cópia recuperável.")
    connection = open_data_store(directory, data_key)
    try:
        migration(connection); connection.commit(); manifest["format_version"] = target_version; _write_manifest(directory, manifest)
    except Exception:
        connection.rollback(); raise DataStoreError("A migração dos dados locais não foi concluída.")
    finally:
        connection.close()
    return backup_path

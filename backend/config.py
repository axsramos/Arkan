"""Configuração local sem efeitos persistentes no carregamento do processo."""

from pathlib import Path
import sys


def application_root() -> Path:
    """Retorna o diretório da cópia executável ou do projeto em desenvolvimento."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = application_root()
STORAGE_DIR = BASE_DIR / "data"
DB_PATH = STORAGE_DIR / "arkan_vault.db"
FILES_DIR = STORAGE_DIR / "files"
CREDENTIALS_PATH = STORAGE_DIR / "credentials.json"
MANIFEST_PATH = STORAGE_DIR / "manifest.json"


def storage_is_activated(storage_dir: Path | str = STORAGE_DIR) -> bool:
    """Indica somente se há um armazenamento confirmado nesta cópia.

    Esta consulta não cria diretórios nem interpreta dados persistidos. A
    validação criptográfica do manifesto pertence à fábrica de armazenamento.
    """
    directory = Path(storage_dir)
    return directory.is_dir() and (directory / "manifest.json").is_file()

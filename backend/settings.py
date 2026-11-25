"""Preferências locais não sensíveis da cópia do Arkan."""

import json
from pathlib import Path


SETTINGS_FORMAT_VERSION = 1
DEFAULT_THEME = "DARK"
_ALLOWED_THEMES = {"DARK", "LIGHT"}


def default_settings() -> dict:
    return {"format_version": SETTINGS_FORMAT_VERSION, "appearance": {"theme": DEFAULT_THEME}}


def load_settings(path: Path) -> dict:
    """Lê somente preferências reconhecidas e usa o padrão em caso de falha."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        theme = raw["appearance"]["theme"]
        if raw.get("format_version") != SETTINGS_FORMAT_VERSION or theme not in _ALLOWED_THEMES:
            return default_settings()
        return {"format_version": SETTINGS_FORMAT_VERSION, "appearance": {"theme": theme}}
    except (OSError, ValueError, TypeError, KeyError):
        return default_settings()


def save_theme(path: Path, theme: str) -> dict:
    """Persiste o tema com troca atômica e backup recuperável da preferência anterior."""
    if theme not in _ALLOWED_THEMES:
        raise ValueError("Tema local inválido.")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        path.with_suffix(path.suffix + ".backup").write_bytes(path.read_bytes())
    settings = {"format_version": SETTINGS_FORMAT_VERSION, "appearance": {"theme": theme}}
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return settings

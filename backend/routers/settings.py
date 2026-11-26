"""Rotas locais para preferências não sensíveis da interface."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import LEGACY_SETTINGS_PATH, SETTINGS_PATH
from backend.settings import load_settings, migrate_legacy_settings, save_theme


router = APIRouter()


class ThemePayload(BaseModel):
    theme: Literal["DARK", "LIGHT"]


@router.get("/api/v1/settings")
async def get_settings() -> dict:
    migrate_legacy_settings(LEGACY_SETTINGS_PATH, SETTINGS_PATH)
    return load_settings(SETTINGS_PATH)


@router.put("/api/v1/settings/theme")
async def update_theme(payload: ThemePayload) -> dict:
    migrate_legacy_settings(LEGACY_SETTINGS_PATH, SETTINGS_PATH)
    return save_theme(SETTINGS_PATH, payload.theme)


__all__ = ["router"]

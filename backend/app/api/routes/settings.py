"""Settings endpoints.

Thin HTTP adapters exposing settings read and update. All logic is
delegated to the settings service.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.models.schemas import Settings
from app.services.download_manager import download_manager
from app.services.settings_service import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=Settings)
async def get_settings() -> Settings:
    """Return the current application settings."""
    return await settings_service.get_all()


@router.put("", response_model=Settings)
async def update_settings(payload: dict[str, Any]) -> Settings:
    """Partially update application settings and return the result."""
    result = await settings_service.update(payload)
    # Apply concurrency changes to the live download engine immediately.
    download_manager.set_concurrency(result.parallel_downloads)
    return result

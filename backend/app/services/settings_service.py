"""Settings service.

Manages application settings persisted in SQLite. Provides defaults and
conversion between the stored string values and the typed Settings
schema. No business logic lives in routes.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.models.schemas import Settings
from app.storage.database import database
from app.storage.settings_repository import SettingsRepository

logger = get_logger(__name__)


class SettingsService:
    """Service for reading and updating persisted application settings."""

    # Defaults mirrored from the Settings schema.
    _DEFAULTS: dict[str, object] = {
        "theme": "dark",
        "download_dir": "",
        "parallel_downloads": 2,
        "default_video_quality": "best",
        "default_audio_format": "mp3",
        "default_audio_quality": "best",
        "filename_template": "%(title)s.%(ext)s",
        "subtitles_enabled": False,
        "proxy": "",
        "bandwidth_limit": "",
        "language": "en",
        "auto_update": True,
        "ffmpeg_path": "",
    }

    def __init__(self, repo: SettingsRepository) -> None:
        self._repo = repo

    async def get_all(self) -> Settings:
        """Return the full settings object, applying stored overrides."""
        stored = await self._repo.get_all()
        values = dict(self._DEFAULTS)
        values.update(self._coerce(stored))
        return Settings(**values)

    async def update(self, updates: dict) -> Settings:
        """Apply partial updates and return the refreshed settings."""
        # Only persist known keys, coercing to strings.
        payload: dict[str, object] = {}
        for key, value in updates.items():
            if key in self._DEFAULTS:
                payload[key] = value
        await self._repo.update_many(self._stringify(payload))
        logger.info("Settings updated: %s", ", ".join(payload.keys()))
        return await self.get_all()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce(stored: dict[str, str]) -> dict[str, object]:
        """Convert a dict of strings back toward their typed defaults."""
        result: dict[str, object] = {}
        for key, raw in stored.items():
            if key in ("parallel_downloads",):
                try:
                    result[key] = int(raw)
                except ValueError:
                    result[key] = 2
            elif key in ("subtitles_enabled", "auto_update"):
                result[key] = raw.lower() in ("true", "1", "yes")
            else:
                result[key] = raw
        return result

    @staticmethod
    def _stringify(values: dict[str, object]) -> dict[str, str]:
        """Convert values to strings for storage."""
        return {key: str(value) for key, value in values.items()}


# Module-level singleton wired with the database-backed repository.
settings_service = SettingsService(SettingsRepository(database))

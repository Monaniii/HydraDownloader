"""Application configuration using pydantic-settings.

Centralises all configurable values for the backend. Values can be
overridden via environment variables prefixed with ``HYDRA_``.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_prefix="HYDRA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Server ---
    app_name: str = "Hydra Downloader API"
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"

    # --- CORS ---
    cors_origins: list[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # --- Analysis ---
    # Maximum time (seconds) allowed for a single metadata extraction.
    analyze_timeout: int = 30

    # --- Downloads ---
    # Default maximum number of simultaneous downloads.
    default_parallel_downloads: int = 2
    # Default output directory when no override is provided.
    default_download_dir: Path = Path.home() / "Downloads" / "Hydra"
    # Default filename template passed to yt-dlp.
    default_filename_template: str = "%(title)s.%(ext)s"
    # Timeout (seconds) for the whole download operation.
    download_timeout: int = 3600
    # Maximum number of automatic retry attempts for transient failures.
    max_retries: int = 3
    # Base delay (seconds) for exponential backoff between retries.
    retry_base_delay: float = 2.0
    # Maximum delay (seconds) between retries.
    retry_max_delay: float = 60.0
    # Whether to auto-resume interrupted downloads on restart.
    auto_resume: bool = True

    @property
    def data_dir(self) -> Path:
        """Directory where persistent app data (DB, logs) is stored."""
        base = Path.home() / ".hydra"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @property
    def log_dir(self) -> Path:
        """Directory for log files."""
        d = self.data_dir / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()

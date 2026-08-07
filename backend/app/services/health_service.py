"""Health check service.

Provides runtime health information about the backend. Kept separate
from the route so the route stays a thin HTTP adapter.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class HealthService:
    """Service that reports backend health status."""

    def check(self) -> dict:
        """Return a health payload with status and version.

        Returns:
            dict: A JSON-serialisable health report.
        """
        logger.debug("Health check requested")
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.version,
        }


# Module-level singleton for dependency injection.
health_service = HealthService()

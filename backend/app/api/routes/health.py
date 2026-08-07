"""Health endpoint route.

Thin HTTP adapter: delegates all logic to HealthService.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services.health_service import HealthService, health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def get_health(service: HealthService = Depends(lambda: health_service)) -> dict:
    """Return backend health status."""
    return service.check()

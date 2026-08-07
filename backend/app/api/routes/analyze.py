"""Analyze endpoint route.

Thin HTTP adapter that delegates all logic to AnalyzerService. No
business logic lives here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.errors import AppError
from app.models.schemas import AnalyzeRequest, ErrorResponse, VideoInfo
from app.services.analyzer_service import AnalyzerService, analyzer_service

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post(
    "",
    response_model=VideoInfo,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        403: {"model": ErrorResponse, "description": "Age-restricted"},
        404: {"model": ErrorResponse, "description": "Unavailable video"},
        422: {"model": ErrorResponse, "description": "Unsupported site"},
        502: {"model": ErrorResponse, "description": "Network error"},
        504: {"model": ErrorResponse, "description": "Timeout"},
    },
)
def analyze_media(
    request: AnalyzeRequest,
    service: AnalyzerService = Depends(lambda: analyzer_service),
) -> VideoInfo:
    """Analyze a media URL and return structured metadata.

    The URL is validated by Pydantic (HttpUrl) and then processed by the
    AnalyzerService. Any AppError raised by the service is translated
    into an appropriate HTTP response.
    """
    try:
        return service.analyze(str(request.url))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

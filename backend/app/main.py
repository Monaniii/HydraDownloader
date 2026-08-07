"""FastAPI application factory for Hydra Downloader.

Creates and configures the FastAPI app, wires routers, CORS, logging,
and initialises the database. No business logic lives here.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.storage.database import database
from app.services.download_manager import download_manager
from app.services.progress_manager import progress_manager
from app.api.routes import (
    analyze,
    download,
    health,
    history,
    queue,
    search,
    ws,
)
from app.api.routes import settings as settings_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: configure logging and initialise storage."""
    configure_logging()
    logger.info("Starting %s v%s", settings.app_name, settings.version)
    # Bind the main event loop so progress updates and history writes
    # can be scheduled thread-safely from download worker threads.
    loop = asyncio.get_running_loop()
    progress_manager.bind_loop(loop)
    download_manager.bind_loop(loop)
    await database.connect()
    logger.info("Database initialised")
    # Restore any persisted queue items and requeue unfinished work so
    # downloads survive application restarts.
    await download_manager.load_persisted()
    logger.info("Queue restored")
    yield
    await database.close()
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — allow the Angular dev server and packaged app.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(analyze.router)
    app.include_router(download.router)
    app.include_router(queue.router)
    app.include_router(history.router)
    app.include_router(settings_router.router)
    app.include_router(search.router)
    app.include_router(ws.router)

    return app


app = create_app()

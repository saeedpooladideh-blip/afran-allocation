from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import Settings, get_settings
from app.crawlers.base import BaseCrawler
from app.crawlers.fipiran import FipiranCrawler
from app.database.session import Database
from app.services.crawl_service import CrawlService
from app.services.scheduler import CrawlScheduler
from app.utils.logging import configure_logging


def create_app(
    settings: Settings | None = None,
    *,
    crawler_factory: Callable[[Settings], BaseCrawler] | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging(resolved_settings.log_level)
        resolved_settings.ensure_sqlite_directory()
        database = Database(resolved_settings.database_url)
        if resolved_settings.database_auto_create:
            database.create_schema()
        crawler = (
            crawler_factory(resolved_settings)
            if crawler_factory is not None
            else FipiranCrawler(resolved_settings)
        )
        crawl_service = CrawlService(
            crawler,
            database.session_factory,
            resolved_settings.fipiran_url,
        )
        scheduler = CrawlScheduler(
            crawl_service,
            resolved_settings.crawl_interval,
            resolved_settings.crawl_on_startup,
        )
        application.state.settings = resolved_settings
        application.state.database = database
        application.state.crawl_service = crawl_service
        application.state.scheduler = scheduler
        if resolved_settings.scheduler_enabled:
            scheduler.start()
        try:
            yield
        finally:
            await scheduler.stop()
            database.dispose()

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Independent Fipiran fund collection and history API for Afran.",
        lifespan=lifespan,
    )

    @application.exception_handler(Exception)
    async def unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_type": type(exc).__name__},
        )

    @application.get("/", tags=["system"])
    async def root(request: Request) -> dict[str, Any]:
        return {
            "status": "healthy",
            "service": resolved_settings.app_name,
            "version": resolved_settings.app_version,
            "source": "Fipiran",
            "links": {
                "health": str(request.url_for("health")),
                "funds": str(request.url_for("list_funds")),
                "status": str(request.url_for("system_status")),
                "docs": str(request.base_url) + "docs",
            },
        }

    application.include_router(router)
    # Versioned aliases make future API changes possible without breaking the MVP paths.
    application.include_router(router, prefix="/api/v1", include_in_schema=False)
    return application


app = create_app()

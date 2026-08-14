from __future__ import annotations

import asyncio
import logging

from app.services.crawl_service import CrawlAlreadyRunning, CrawlService

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """Single-process interval scheduler; use one worker when enabled."""

    def __init__(self, service: CrawlService, interval_seconds: int, run_on_startup: bool) -> None:
        self.service = service
        self.interval_seconds = interval_seconds
        self.run_on_startup = run_on_startup
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run_loop(), name="fipiran-scheduler")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run_loop(self) -> None:
        if self.run_on_startup:
            await self._run_once()
        while True:
            await asyncio.sleep(self.interval_seconds)
            await self._run_once()

    async def _run_once(self) -> None:
        try:
            await self.service.run()
        except CrawlAlreadyRunning:
            logger.info("Scheduled crawl skipped because another crawl is active")
        except Exception:
            logger.exception("Scheduled crawl failed")

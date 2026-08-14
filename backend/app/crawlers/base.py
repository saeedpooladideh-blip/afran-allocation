from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.crawlers.app_types import CrawlResult


class CrawlerError(RuntimeError):
    """Expected upstream or parsing failure."""


class BaseCrawler(ABC):
    """Contract implemented by every future data source adapter."""

    source_name: str

    @abstractmethod
    async def probe(self) -> dict[str, Any]:
        """Check source connectivity without persisting data."""

    @abstractmethod
    async def crawl(self) -> CrawlResult:
        """Return canonical records independent of the source schema."""

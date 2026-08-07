from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    funds_inserted: Mapped[int] = mapped_column(Integer, default=0)
    funds_updated: Mapped[int] = mapped_column(Integer, default=0)
    navs_inserted: Mapped[int] = mapped_column(Integer, default=0)
    performances_inserted: Mapped[int] = mapped_column(Integer, default=0)
    managers_upserted: Mapped[int] = mapped_column(Integer, default=0)
    exposures_inserted: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str] = mapped_column(Text)
    diagnostics: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

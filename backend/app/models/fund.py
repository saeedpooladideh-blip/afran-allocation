from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.exposure import FundExposure
    from app.models.manager import FundManager
    from app.models.nav import FundNAV
    from app.models.performance import FundPerformance


def utc_now() -> datetime:
    return datetime.now(UTC)


class Fund(Base):
    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    symbol: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    fund_type_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    fund_type_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    investment_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    initiation_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_updated_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    raw_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    nav_history: Mapped[list[FundNAV]] = relationship(
        back_populates="fund", cascade="all, delete-orphan"
    )
    performance_history: Mapped[list[FundPerformance]] = relationship(
        back_populates="fund", cascade="all, delete-orphan"
    )
    managers: Mapped[list[FundManager]] = relationship(
        back_populates="fund", cascade="all, delete-orphan"
    )
    exposure_history: Mapped[list[FundExposure]] = relationship(
        back_populates="fund", cascade="all, delete-orphan"
    )

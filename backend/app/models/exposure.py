from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.fund import Fund


class FundExposure(Base):
    """Append-only Fipiran portfolio composition observation.

    Percentages are stored in percentage-point units.  ``equity_exposure`` is
    materialized at collection time so a historical record is never silently
    recalculated after parser or model changes.
    """

    __tablename__ = "fund_exposures"
    __table_args__ = (
        UniqueConstraint("fund_id", "report_date", name="uq_fund_exposure_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(
        ForeignKey("funds.id", ondelete="CASCADE"), index=True
    )
    report_date: Mapped[str] = mapped_column(String(32), index=True)
    stock_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    equity_fund_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), nullable=True
    )
    fixed_income_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), nullable=True
    )
    cash_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    deposit_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    other_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    commodity_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), nullable=True
    )
    equity_exposure: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="fipiran-api")
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    raw_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    fund: Mapped[Fund] = relationship(back_populates="exposure_history")

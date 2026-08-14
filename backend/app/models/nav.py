from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.fund import Fund


class FundNAV(Base):
    __tablename__ = "fund_navs"
    __table_args__ = (UniqueConstraint("fund_id", "nav_date", name="uq_fund_nav_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id", ondelete="CASCADE"), index=True)
    nav_date: Mapped[str] = mapped_column(String(32), index=True)
    issue_nav: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    cancel_nav: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    statistical_nav: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    net_asset: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    unit_count: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    units_issued: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    units_redeemed: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    raw_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    fund: Mapped[Fund] = relationship(back_populates="nav_history")

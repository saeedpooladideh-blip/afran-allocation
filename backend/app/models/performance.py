from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.fund import Fund


class FundPerformance(Base):
    __tablename__ = "fund_performances"
    __table_args__ = (
        UniqueConstraint("fund_id", "as_of_date", name="uq_fund_performance_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id", ondelete="CASCADE"), index=True)
    as_of_date: Mapped[str] = mapped_column(String(32), index=True)
    daily_return: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    weekly_return: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    monthly_return: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    quarterly_return: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    six_month_return: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    annual_return: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    since_inception_return: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    alpha: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    beta: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    raw_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    fund: Mapped[Fund] = relationship(back_populates="performance_history")

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.fund import Fund


class FundManager(Base):
    __tablename__ = "fund_managers"
    __table_args__ = (
        UniqueConstraint("fund_id", "role", "name", name="uq_fund_manager_role_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    raw_data: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    fund: Mapped[Fund] = relationship(back_populates="managers")

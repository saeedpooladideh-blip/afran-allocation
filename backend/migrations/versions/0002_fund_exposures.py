"""Add append-only portfolio composition observations.

Revision ID: 0002_fund_exposures
Revises: 0001_initial
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_fund_exposures"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crawl_logs",
        sa.Column("exposures_inserted", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "fund_exposures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.String(length=32), nullable=False),
        sa.Column("stock_percentage", sa.Numeric(12, 6), nullable=True),
        sa.Column("equity_fund_percentage", sa.Numeric(12, 6), nullable=True),
        sa.Column("fixed_income_percentage", sa.Numeric(12, 6), nullable=True),
        sa.Column("cash_percentage", sa.Numeric(12, 6), nullable=True),
        sa.Column("deposit_percentage", sa.Numeric(12, 6), nullable=True),
        sa.Column("other_percentage", sa.Numeric(12, 6), nullable=True),
        sa.Column("commodity_percentage", sa.Numeric(12, 6), nullable=True),
        sa.Column("equity_exposure", sa.Numeric(12, 6), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("fund_id", "report_date", name="uq_fund_exposure_date"),
    )
    op.create_index("ix_fund_exposures_fund_id", "fund_exposures", ["fund_id"])
    op.create_index("ix_fund_exposures_report_date", "fund_exposures", ["report_date"])
    op.create_index(
        "ix_fund_exposures_calculated_at", "fund_exposures", ["calculated_at"]
    )
    op.create_index("ix_fund_exposures_retrieved_at", "fund_exposures", ["retrieved_at"])


def downgrade() -> None:
    op.drop_table("fund_exposures")
    op.drop_column("crawl_logs", "exposures_inserted")

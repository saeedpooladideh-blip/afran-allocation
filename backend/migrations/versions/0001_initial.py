"""Create the initial Afran fund data schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "funds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("symbol", sa.String(length=128), nullable=True),
        sa.Column("fund_type_code", sa.String(length=64), nullable=True),
        sa.Column("fund_type_name", sa.String(length=255), nullable=True),
        sa.Column("investment_type", sa.String(length=128), nullable=True),
        sa.Column("initiation_date", sa.String(length=32), nullable=True),
        sa.Column("source_updated_at", sa.String(length=64), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("national_id", sa.String(length=64), nullable=True),
        sa.Column("registration_number", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.UniqueConstraint("external_id", name="uq_funds_external_id"),
    )
    op.create_index("ix_funds_external_id", "funds", ["external_id"])
    op.create_index("ix_funds_name", "funds", ["name"])
    op.create_index("ix_funds_symbol", "funds", ["symbol"])
    op.create_index("ix_funds_fund_type_code", "funds", ["fund_type_code"])
    op.create_index("ix_funds_fund_type_name", "funds", ["fund_type_name"])

    op.create_table(
        "crawl_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=True),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("funds_inserted", sa.Integer(), nullable=False),
        sa.Column("funds_updated", sa.Integer(), nullable=False),
        sa.Column("navs_inserted", sa.Integer(), nullable=False),
        sa.Column("performances_inserted", sa.Integer(), nullable=False),
        sa.Column("managers_upserted", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=True),
    )
    op.create_index("ix_crawl_logs_started_at", "crawl_logs", ["started_at"])
    op.create_index("ix_crawl_logs_status", "crawl_logs", ["status"])

    op.create_table(
        "fund_navs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("nav_date", sa.String(length=32), nullable=False),
        sa.Column("issue_nav", sa.Numeric(24, 6), nullable=True),
        sa.Column("cancel_nav", sa.Numeric(24, 6), nullable=True),
        sa.Column("statistical_nav", sa.Numeric(24, 6), nullable=True),
        sa.Column("net_asset", sa.Numeric(30, 6), nullable=True),
        sa.Column("unit_count", sa.Numeric(30, 6), nullable=True),
        sa.Column("units_issued", sa.Numeric(30, 6), nullable=True),
        sa.Column("units_redeemed", sa.Numeric(30, 6), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("fund_id", "nav_date", name="uq_fund_nav_date"),
    )
    op.create_index("ix_fund_navs_fund_id", "fund_navs", ["fund_id"])
    op.create_index("ix_fund_navs_nav_date", "fund_navs", ["nav_date"])
    op.create_index("ix_fund_navs_retrieved_at", "fund_navs", ["retrieved_at"])

    op.create_table(
        "fund_performances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("as_of_date", sa.String(length=32), nullable=False),
        sa.Column("daily_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("weekly_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("monthly_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("quarterly_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("six_month_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("annual_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("since_inception_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("alpha", sa.Numeric(16, 8), nullable=True),
        sa.Column("beta", sa.Numeric(16, 8), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("fund_id", "as_of_date", name="uq_fund_performance_date"),
    )
    op.create_index("ix_fund_performances_fund_id", "fund_performances", ["fund_id"])
    op.create_index("ix_fund_performances_as_of_date", "fund_performances", ["as_of_date"])
    op.create_index("ix_fund_performances_retrieved_at", "fund_performances", ["retrieved_at"])

    op.create_table(
        "fund_managers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("fund_id", "role", "name", name="uq_fund_manager_role_name"),
    )
    op.create_index("ix_fund_managers_fund_id", "fund_managers", ["fund_id"])
    op.create_index("ix_fund_managers_role", "fund_managers", ["role"])
    op.create_index("ix_fund_managers_name", "fund_managers", ["name"])


def downgrade() -> None:
    op.drop_table("fund_managers")
    op.drop_table("fund_performances")
    op.drop_table("fund_navs")
    op.drop_table("crawl_logs")
    op.drop_table("funds")

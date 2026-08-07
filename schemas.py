from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NAVOut(ORMModel):
    nav_date: str
    issue_nav: Decimal | None
    cancel_nav: Decimal | None
    statistical_nav: Decimal | None
    net_asset: Decimal | None
    unit_count: Decimal | None
    units_issued: Decimal | None
    units_redeemed: Decimal | None
    retrieved_at: datetime


class PerformanceOut(ORMModel):
    as_of_date: str
    daily_return: Decimal | None
    weekly_return: Decimal | None
    monthly_return: Decimal | None
    quarterly_return: Decimal | None
    six_month_return: Decimal | None
    annual_return: Decimal | None
    since_inception_return: Decimal | None
    alpha: Decimal | None
    beta: Decimal | None
    retrieved_at: datetime


class ManagerOut(ORMModel):
    role: str
    name: str
    external_id: str | None
    first_seen_at: datetime
    last_seen_at: datetime


class ExposureOut(ORMModel):
    id: int
    fund_id: int
    report_date: str
    stock_percentage: Decimal | None
    equity_fund_percentage: Decimal | None
    fixed_income_percentage: Decimal | None
    cash_percentage: Decimal | None
    deposit_percentage: Decimal | None
    other_percentage: Decimal | None
    commodity_percentage: Decimal | None
    equity_exposure: Decimal | None
    source: str
    calculated_at: datetime
    retrieved_at: datetime


class FundSummary(ORMModel):
    id: int
    external_id: str
    name: str
    symbol: str | None
    fund_type_code: str | None
    fund_type_name: str | None
    investment_type: str | None
    source_updated_at: str | None
    website: str | None
    is_active: bool
    last_seen_at: datetime
    latest_nav: NAVOut | None = None
    latest_exposure: ExposureOut | None = None


class FundDetail(FundSummary):
    initiation_date: str | None
    national_id: str | None
    registration_number: str | None
    first_seen_at: datetime
    latest_performance: PerformanceOut | None = None
    managers: list[ManagerOut] = Field(default_factory=list)


class FundListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[FundSummary]


class FundHistoryResponse(BaseModel):
    fund_id: int
    total: int
    offset: int
    limit: int
    items: list[NAVOut]


class FundExposureResponse(BaseModel):
    fund_id: int
    fund_name: str
    benchmark_bm: Decimal
    latest: ExposureOut | None


class ExposureRankingItem(BaseModel):
    rank: int
    fund_id: int
    external_id: str
    name: str
    symbol: str | None
    fund_type_name: str | None
    exposure: ExposureOut


class ExposureRankingResponse(BaseModel):
    benchmark_bm: Decimal
    total_funds: int
    ranked_funds: int
    missing_exposure_funds: int
    items: list[ExposureRankingItem]


class CrawlOut(BaseModel):
    crawl_id: int
    status: str
    method: str
    records_received: int
    funds_inserted: int
    funds_updated: int
    navs_inserted: int
    performances_inserted: int
    managers_upserted: int
    exposures_inserted: int
    error_count: int
    duration_ms: int


class CrawlAccepted(BaseModel):
    status: str = "accepted"
    message: str


class CrawlLogOut(ORMModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    method: str | None
    records_received: int
    exposures_inserted: int
    error_count: int
    error_message: str | None
    duration_ms: int | None


class SystemStatus(BaseModel):
    service: str
    version: str
    database: str
    crawler_running: bool
    scheduler_enabled: bool
    source: str
    counts: dict[str, int]
    latest_crawl: CrawlLogOut | None
    latest_successful_crawl: CrawlLogOut | None
    last_runtime_error: str | None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    source: str
    latest_successful_crawl_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)

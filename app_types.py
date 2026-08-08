from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class FundRecord:
    external_id: str
    name: str
    symbol: str | None = None
    fund_type_code: str | None = None
    fund_type_name: str | None = None
    investment_type: str | None = None
    initiation_date: str | None = None
    source_updated_at: str | None = None
    website: str | None = None
    national_id: str | None = None
    registration_number: str | None = None
    is_active: bool = True
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NAVRecord:
    external_id: str
    nav_date: str
    issue_nav: Decimal | None = None
    cancel_nav: Decimal | None = None
    statistical_nav: Decimal | None = None
    net_asset: Decimal | None = None
    unit_count: Decimal | None = None
    units_issued: Decimal | None = None
    units_redeemed: Decimal | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PerformanceRecord:
    external_id: str
    as_of_date: str
    daily_return: Decimal | None = None
    weekly_return: Decimal | None = None
    monthly_return: Decimal | None = None
    quarterly_return: Decimal | None = None
    six_month_return: Decimal | None = None
    annual_return: Decimal | None = None
    since_inception_return: Decimal | None = None
    alpha: Decimal | None = None
    beta: Decimal | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ManagerRecord:
    external_id: str
    role: str
    name: str
    manager_external_id: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExposureRecord:
    external_id: str
    report_date: str
    stock_percentage: Decimal | None = None
    equity_fund_percentage: Decimal | None = None
    fixed_income_percentage: Decimal | None = None
    cash_percentage: Decimal | None = None
    deposit_percentage: Decimal | None = None
    other_percentage: Decimal | None = None
    commodity_percentage: Decimal | None = None
    equity_exposure: Decimal | None = None
    source: str = "fipiran-api"
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CrawlResult:
    method: str
    funds: list[FundRecord] = field(default_factory=list)
    navs: list[NAVRecord] = field(default_factory=list)
    performances: list[PerformanceRecord] = field(default_factory=list)
    managers: list[ManagerRecord] = field(default_factory=list)
    exposures: list[ExposureRecord] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def record_count(self) -> int:
        return len(self.funds)

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from app.crawlers.base import CrawlerError
from app.crawlers.app_types import (
    ExposureRecord,
    FundRecord,
    ManagerRecord,
    NAVRecord,
    PerformanceRecord,
)

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class DataParser:
    """Translate unstable Fipiran payloads into a stable internal contract."""

    @staticmethod
    def unwrap_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            raise CrawlerError("Fipiran response is neither an object nor a list")
        for key in ("items", "Items", "data", "Data", "result", "Result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = DataParser.unwrap_items(value)
                if nested:
                    return nested
        item = payload.get("item") or payload.get("Item")
        if isinstance(item, dict):
            return [item]
        return []

    @staticmethod
    def unwrap_item(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        for key in ("item", "Item", "data", "Data", "result", "Result"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        return payload

    @staticmethod
    def pick(data: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in data and data[key] not in (None, ""):
                return data[key]
        lowered = {str(key).lower(): value for key, value in data.items()}
        for key in keys:
            value = lowered.get(key.lower())
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, dict):
            for key in ("name", "title", "value", "text"):
                if value.get(key) not in (None, ""):
                    return str(value[key]).strip() or None
            return None
        result = str(value).strip()
        return result or None

    @staticmethod
    def decimal(value: Any) -> Decimal | None:
        if value in (None, "", "-", "--"):
            return None
        if isinstance(value, bool):
            return None
        normalized = str(value).translate(PERSIAN_DIGITS).strip()
        normalized = (
            normalized.replace(",", "")
            .replace("٬", "")
            .replace("٫", ".")
            .replace("٪", "")
        )
        normalized = normalized.replace("%", "").replace("−", "-")
        try:
            return Decimal(normalized)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def date(value: Any) -> str | None:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            seconds = float(value) / 1000 if value > 10_000_000_000 else float(value)
            return datetime.fromtimestamp(seconds, UTC).date().isoformat()
        normalized = str(value).translate(PERSIAN_DIGITS).strip()
        match = re.search(r"/Date\((\d+)", normalized)
        if match:
            return datetime.fromtimestamp(int(match.group(1)) / 1000, UTC).date().isoformat()
        # Preserve Jalali values as supplied; converting them incorrectly is worse.
        if re.fullmatch(r"1[34]\d{2}[-/]\d{1,2}[-/]\d{1,2}", normalized):
            return normalized.replace("/", "-")
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            match = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", normalized)
            return match.group(0).replace("/", "-") if match else normalized[:32]

    def parse_fund_list(
        self, payload: Any, fund_types: dict[str, str] | None = None
    ) -> list[FundRecord]:
        records: list[FundRecord] = []
        for item in self.unwrap_items(payload):
            external_id = self.text(self.pick(item, "regNo", "regno", "registrationNo", "id"))
            name = self.text(self.pick(item, "name", "fundName", "title"))
            if not external_id or not name:
                continue
            type_value = self.pick(item, "fundType", "fundTypeId", "type")
            type_code = self.text(type_value)
            type_name = self.text(self.pick(item, "fundTypeName", "typeName"))
            if not type_name and type_code and fund_types:
                type_name = fund_types.get(type_code)
            records.append(
                FundRecord(
                    external_id=external_id,
                    name=name,
                    symbol=self.text(self.pick(item, "smallSymbolName", "symbol", "symbolName")),
                    fund_type_code=type_code,
                    fund_type_name=type_name,
                    investment_type=self.text(self.pick(item, "typeOfInvest", "investmentType")),
                    initiation_date=self.date(self.pick(item, "initiationDate", "startDate")),
                    source_updated_at=self.date(self.pick(item, "date", "updateDate", "lastUpdate")),
                    website=self.text(self.pick(item, "websiteAddress", "website", "url")),
                    national_id=self.text(self.pick(item, "nationalId")),
                    registration_number=self.text(self.pick(item, "registrationNumber")),
                    is_active=self.boolean(self.pick(item, "isActive"), default=True),
                    raw_data=item,
                )
            )
        return records

    @staticmethod
    def boolean(value: Any, *, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() not in {"false", "0", "no", "inactive", "غیرفعال"}

    def parse_fund_types(self, payload: Any) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in self.unwrap_items(payload):
            code = self.text(self.pick(item, "fundType", "id", "value"))
            name = self.text(self.pick(item, "name", "title"))
            if code and name:
                result[code] = name
        return result

    def enrich_fund(self, fund: FundRecord, payload: Any) -> FundRecord:
        detail = self.unwrap_item(payload)
        if not detail:
            return fund
        fund.name = self.text(self.pick(detail, "name", "fundName")) or fund.name
        fund.symbol = self.text(self.pick(detail, "smallSymbolName", "symbol")) or fund.symbol
        fund.fund_type_name = (
            self.text(self.pick(detail, "fundTypeName", "typeName")) or fund.fund_type_name
        )
        fund.investment_type = (
            self.text(self.pick(detail, "typeOfInvest", "investmentType")) or fund.investment_type
        )
        fund.website = self.text(self.pick(detail, "websiteAddress", "website")) or fund.website
        fund.national_id = self.text(self.pick(detail, "nationalId")) or fund.national_id
        fund.registration_number = (
            self.text(self.pick(detail, "registrationNumber")) or fund.registration_number
        )
        fund.source_updated_at = (
            self.date(self.pick(detail, "date", "updateDate")) or fund.source_updated_at
        )
        fund.raw_data = {**fund.raw_data, **detail}
        return fund

    def parse_current_nav(self, fund: FundRecord) -> NAVRecord | None:
        item = fund.raw_data
        nav_date = self.date(self.pick(item, "date", "updateDate", "lastUpdate"))
        if not nav_date:
            return None
        values = {
            "issue_nav": self.decimal(self.pick(item, "issueNav", "issuanceNav")),
            "cancel_nav": self.decimal(self.pick(item, "cancelNav", "redemptionNav")),
            "statistical_nav": self.decimal(self.pick(item, "statisticalNav")),
            "net_asset": self.decimal(self.pick(item, "netAsset", "totalNetAsset")),
            "unit_count": self.decimal(self.pick(item, "investedUnits", "fundUnit", "unitCount")),
        }
        if all(value is None for value in values.values()):
            return None
        return NAVRecord(fund.external_id, nav_date, raw_data=item, **values)

    def parse_nav_history(self, external_id: str, payload: Any) -> list[NAVRecord]:
        records: list[NAVRecord] = []
        for item in self.unwrap_items(payload):
            nav_date = self.date(self.pick(item, "date", "navDate", "reportDate"))
            if not nav_date:
                continue
            records.append(
                NAVRecord(
                    external_id=external_id,
                    nav_date=nav_date,
                    issue_nav=self.decimal(self.pick(item, "issueNav", "issuanceNav")),
                    cancel_nav=self.decimal(self.pick(item, "cancelNav", "redemptionNav")),
                    statistical_nav=self.decimal(self.pick(item, "statisticalNav")),
                    raw_data=item,
                )
            )
        return records

    def parse_net_asset_history(self, external_id: str, payload: Any) -> list[NAVRecord]:
        records: list[NAVRecord] = []
        for item in self.unwrap_items(payload):
            nav_date = self.date(self.pick(item, "date", "navDate", "reportDate"))
            if not nav_date:
                continue
            records.append(
                NAVRecord(
                    external_id=external_id,
                    nav_date=nav_date,
                    net_asset=self.decimal(self.pick(item, "netAsset", "totalNetAsset")),
                    unit_count=self.decimal(self.pick(item, "unitCount", "fundUnit", "investedUnits")),
                    units_issued=self.decimal(self.pick(item, "unitsSubDAY", "issuedUnits")),
                    units_redeemed=self.decimal(self.pick(item, "unitsRedDAY", "redeemedUnits")),
                    raw_data=item,
                )
            )
        return records

    def merge_nav_records(self, groups: Iterable[list[NAVRecord]]) -> list[NAVRecord]:
        merged: dict[tuple[str, str], NAVRecord] = {}
        for group in groups:
            for record in group:
                key = (record.external_id, record.nav_date)
                current = merged.get(key)
                if current is None:
                    merged[key] = record
                    continue
                for field_name in (
                    "issue_nav",
                    "cancel_nav",
                    "statistical_nav",
                    "net_asset",
                    "unit_count",
                    "units_issued",
                    "units_redeemed",
                ):
                    value = getattr(record, field_name)
                    if value is not None:
                        setattr(current, field_name, value)
                current.raw_data = {**current.raw_data, **record.raw_data}
        return sorted(merged.values(), key=lambda row: (row.external_id, row.nav_date))

    def parse_current_exposure(self, fund: FundRecord) -> ExposureRecord | None:
        """Parse the latest allocation from Fipiran's fund list/detail payload."""

        item = fund.raw_data
        report_date = self.date(
            self.pick(item, "date", "reportDate", "updateDate", "lastModificationTime")
        ) or fund.source_updated_at
        if not report_date:
            return None
        return self._build_exposure(
            external_id=fund.external_id,
            report_date=report_date,
            item=item,
        )

    def parse_portfolio_history(
        self, external_id: str, payload: Any
    ) -> list[ExposureRecord]:
        """Parse ``chart/portfoliochart`` without turning missing values into zero."""

        records: list[ExposureRecord] = []
        for item in self.unwrap_items(payload):
            report_date = self.date(self.pick(item, "date", "reportDate"))
            if not report_date:
                continue
            record = self._build_exposure(
                external_id=external_id,
                report_date=report_date,
                item=item,
            )
            if record is not None:
                records.append(record)
        return records

    def _build_exposure(
        self,
        *,
        external_id: str,
        report_date: str,
        item: dict[str, Any],
    ) -> ExposureRecord | None:
        stock = self.decimal(self.pick(item, "stock", "stockPercentage"))
        equity_fund = self.decimal(
            self.pick(item, "fundUnit", "equityFund", "equityFundPercentage")
        )
        fixed_income = self.decimal(
            self.pick(item, "bond", "fixedIncome", "fixedIncomePercentage")
        )
        cash = self.decimal(self.pick(item, "cash", "cashPercentage"))
        deposit = self.decimal(self.pick(item, "deposit", "depositPercentage"))
        other = self.decimal(self.pick(item, "other", "otherPercentage"))
        commodity = self.decimal(self.pick(item, "commodity", "commodityPercentage"))
        components = (stock, equity_fund, fixed_income, cash, deposit, other, commodity)
        if all(value is None for value in components):
            return None
        equity_exposure = (
            stock + equity_fund if stock is not None and equity_fund is not None else None
        )
        return ExposureRecord(
            external_id=external_id,
            report_date=report_date,
            stock_percentage=stock,
            equity_fund_percentage=equity_fund,
            fixed_income_percentage=fixed_income,
            cash_percentage=cash,
            deposit_percentage=deposit,
            other_percentage=other,
            commodity_percentage=commodity,
            equity_exposure=equity_exposure,
            raw_data=item,
        )

    @staticmethod
    def merge_exposure_records(
        groups: Iterable[list[ExposureRecord]],
    ) -> list[ExposureRecord]:
        """Merge same-date API views before the append-only database write."""

        merged: dict[tuple[str, str], ExposureRecord] = {}
        percentage_fields = (
            "stock_percentage",
            "equity_fund_percentage",
            "fixed_income_percentage",
            "cash_percentage",
            "deposit_percentage",
            "other_percentage",
            "commodity_percentage",
        )
        for group in groups:
            for record in group:
                key = (record.external_id, record.report_date)
                current = merged.get(key)
                if current is None:
                    merged[key] = record
                    continue
                for field_name in percentage_fields:
                    value = getattr(record, field_name)
                    if value is not None:
                        setattr(current, field_name, value)
                current.raw_data = {**current.raw_data, **record.raw_data}
                if (
                    current.stock_percentage is not None
                    and current.equity_fund_percentage is not None
                ):
                    current.equity_exposure = (
                        current.stock_percentage + current.equity_fund_percentage
                    )
        return sorted(merged.values(), key=lambda row: (row.external_id, row.report_date))

    def parse_performance(self, fund: FundRecord) -> PerformanceRecord | None:
        item = fund.raw_data
        as_of_date = self.date(self.pick(item, "date", "updateDate"))
        if not as_of_date:
            return None
        values = {
            "daily_return": self.decimal(self.pick(item, "dailyEfficiency", "dailyReturn")),
            "weekly_return": self.decimal(self.pick(item, "weeklyEfficiency", "weeklyReturn")),
            "monthly_return": self.decimal(self.pick(item, "monthlyEfficiency", "monthlyReturn")),
            "quarterly_return": self.decimal(self.pick(item, "quarterlyEfficiency", "quarterlyReturn")),
            "six_month_return": self.decimal(self.pick(item, "sixMonthEfficiency", "sixMonthReturn")),
            "annual_return": self.decimal(self.pick(item, "annualEfficiency", "annualReturn")),
            "since_inception_return": self.decimal(self.pick(item, "efficiency", "totalReturn")),
            "alpha": self.decimal(self.pick(item, "alpha")),
            "beta": self.decimal(self.pick(item, "beta")),
        }
        if all(value is None for value in values.values()):
            return None
        return PerformanceRecord(fund.external_id, as_of_date, raw_data=item, **values)

    def parse_managers(self, fund: FundRecord) -> list[ManagerRecord]:
        item = fund.raw_data
        roles = {
            "manager": ("manager", "managerSeoRegisterNo"),
            "executive_manager": ("executiveManager", "executiveManagerRegisterNo"),
            "investment_manager": ("investmentManager", "investmentManagerRegisterNo"),
            "auditor": ("auditor", "auditorRegisterNo"),
            "custodian": ("custodian", "custodianRegisterNo"),
            "guarantor": ("guarantor", "guarantorRegisterNo"),
            "market_maker": ("marketMaker", "marketMakerRegisterNo"),
        }
        records: list[ManagerRecord] = []
        for role, (name_key, id_key) in roles.items():
            raw_value = self.pick(item, name_key)
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            for value in values:
                name = self.text(value)
                if not name:
                    continue
                external_id = None
                if isinstance(value, dict):
                    external_id = self.text(self.pick(value, "id", "regNo", "registerNo"))
                external_id = external_id or self.text(self.pick(item, id_key))
                records.append(
                    ManagerRecord(
                        external_id=fund.external_id,
                        role=role,
                        name=name,
                        manager_external_id=external_id,
                        raw_data=value if isinstance(value, dict) else {"value": value},
                    )
                )
        return records

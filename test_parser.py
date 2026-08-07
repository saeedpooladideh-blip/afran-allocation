from __future__ import annotations

from decimal import Decimal

from app.crawlers.parser import DataParser


def test_parser_builds_canonical_records(fixture_json) -> None:
    parser = DataParser()
    fund_types = parser.parse_fund_types(fixture_json("fund_types.json"))
    funds = parser.parse_fund_list(fixture_json("fund_compare.json"), fund_types)
    assert len(funds) == 1
    fund = parser.enrich_fund(funds[0], fixture_json("fund_detail.json"))
    assert fund.external_id == "TEST-1001"
    assert fund.fund_type_name == "در سهام"
    assert fund.website == "https://example.invalid/fund"

    navs = parser.merge_nav_records(
        [
            parser.parse_nav_history(fund.external_id, fixture_json("nav_history.json")),
            parser.parse_net_asset_history(
                fund.external_id, fixture_json("net_asset_history.json")
            ),
        ]
    )
    assert len(navs) == 2
    assert navs[-1].cancel_nav == Decimal("10380")
    assert navs[-1].net_asset == Decimal("9876543210")
    assert navs[-1].units_issued == Decimal("1700")

    exposures = parser.merge_exposure_records(
        [
            parser.parse_portfolio_history(
                fund.external_id, fixture_json("portfolio_history.json")
            ),
            [parser.parse_current_exposure(fund)],
        ]
    )
    assert len(exposures) == 2
    assert exposures[-1].stock_percentage == Decimal("91.4")
    assert exposures[-1].equity_fund_percentage == Decimal("2.6")
    assert exposures[-1].equity_exposure == Decimal("94.0")

    performance = parser.parse_performance(fund)
    assert performance is not None
    assert performance.annual_return == Decimal("37.5")
    assert {manager.role for manager in parser.parse_managers(fund)} == {
        "manager",
        "executive_manager",
        "auditor",
    }


def test_parser_handles_persian_numbers_and_missing_values() -> None:
    parser = DataParser()
    assert parser.decimal("۱٬۲۳۴٫۵") == Decimal("1234.5")
    assert parser.decimal("۱,۲۳۴.۵٪") == Decimal("1234.5")
    assert parser.decimal(None) is None
    assert parser.date("۱۴۰۵/۰۵/۱۶") == "1405-05-16"

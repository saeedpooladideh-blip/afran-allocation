from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.config import Settings
from app.crawlers.base import BaseCrawler
from app.crawlers.types import (
    CrawlResult,
    ExposureRecord,
    FundRecord,
    ManagerRecord,
    NAVRecord,
    PerformanceRecord,
)
from app.main import create_app


class FakeCrawler(BaseCrawler):
    source_name = "test"

    async def probe(self):
        return {"ok": True}

    async def crawl(self) -> CrawlResult:
        return CrawlResult(
            method="api",
            funds=[
                FundRecord(
                    external_id="TEST-1001",
                    name="صندوق آزمون یکپارچه",
                    symbol="آزمون",
                    fund_type_code="1",
                    fund_type_name="در سهام",
                    source_updated_at="2026-08-06",
                )
            ],
            navs=[
                NAVRecord(
                    external_id="TEST-1001",
                    nav_date="2026-08-06",
                    issue_nav=Decimal("10420"),
                    cancel_nav=Decimal("10380"),
                    net_asset=Decimal("9876543210"),
                    unit_count=Decimal("950000"),
                )
            ],
            performances=[
                PerformanceRecord(
                    external_id="TEST-1001",
                    as_of_date="2026-08-06",
                    daily_return=Decimal("0.21"),
                    annual_return=Decimal("37.5"),
                )
            ],
            managers=[
                ManagerRecord(
                    external_id="TEST-1001",
                    role="manager",
                    name="مدیر آزمون",
                )
            ],
            exposures=[
                ExposureRecord(
                    external_id="TEST-1001",
                    report_date="2026-08-06",
                    stock_percentage=Decimal("91.4"),
                    equity_fund_percentage=Decimal("2.6"),
                    fixed_income_percentage=Decimal("1.2"),
                    cash_percentage=Decimal("0.8"),
                    equity_exposure=Decimal("94.0"),
                    source="test-fixture",
                )
            ],
        )


class FailingCrawler(BaseCrawler):
    source_name = "test-failure"

    async def probe(self):
        return {"ok": False}

    async def crawl(self) -> CrawlResult:
        raise RuntimeError("controlled upstream failure")


def build_test_app(database_url: str):
    settings = Settings(
        database_url=database_url,
        scheduler_enabled=False,
        playwright_enabled=False,
        log_level="WARNING",
    )
    return create_app(settings, crawler_factory=lambda _: FakeCrawler())


def test_health_crawl_database_and_read_endpoints(tmp_path) -> None:
    database_path = tmp_path / "afran-test.db"
    app = build_test_app(f"sqlite:///{database_path}")
    with TestClient(app) as client:
        assert database_path.exists()
        assert client.get("/").json()["status"] == "healthy"
        assert client.get("/health").json()["status"] == "healthy"

        crawl = client.post("/crawl?wait=true")
        assert crawl.status_code == 202
        assert crawl.json()["status"] == "success"

        funds = client.get("/funds").json()
        assert funds["total"] == 1
        fund_id = funds["items"][0]["id"]
        assert funds["items"][0]["latest_nav"]["cancel_nav"] == "10380.000000"
        assert funds["items"][0]["latest_exposure"]["equity_exposure"] == "94.000000"

        detail = client.get(f"/funds/{fund_id}")
        assert detail.status_code == 200
        assert detail.json()["managers"][0]["name"] == "مدیر آزمون"

        history = client.get(f"/funds/{fund_id}/history").json()
        assert history["total"] == 1

        exposure = client.get(f"/api/v1/funds/{fund_id}/exposure").json()
        assert exposure["benchmark_bm"] == "2.99"
        assert exposure["latest"]["equity_fund_percentage"] == "2.600000"

        ranking = client.get("/api/v1/exposure/ranking").json()
        assert ranking["ranked_funds"] == 1
        assert ranking["missing_exposure_funds"] == 0
        assert ranking["items"][0]["exposure"]["equity_exposure"] == "94.000000"

        second_crawl = client.post("/crawl?wait=true").json()
        assert second_crawl["funds_updated"] == 1
        assert second_crawl["navs_inserted"] == 0
        assert second_crawl["exposures_inserted"] == 0
        assert client.get("/api/v1/funds").status_code == 200

        status = client.get("/status").json()
        assert status["counts"]["crawl_runs"] == 2
        assert status["latest_successful_crawl"]["status"] == "success"


def test_unknown_fund_is_404(tmp_path) -> None:
    app = build_test_app(f"sqlite:///{tmp_path / 'empty.db'}")
    with TestClient(app) as client:
        assert client.get("/funds/999").status_code == 404


def test_crawl_failure_is_logged_without_stopping_api(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'failure.db'}",
        scheduler_enabled=False,
        log_level="CRITICAL",
    )
    app = create_app(settings, crawler_factory=lambda _: FailingCrawler())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/crawl?wait=true")
        assert response.status_code == 502
        status_payload = client.get("/status").json()
        assert status_payload["latest_crawl"]["status"] == "failed"
        assert "controlled upstream failure" in status_payload["latest_crawl"]["error_message"]
        assert client.get("/health").status_code == 200

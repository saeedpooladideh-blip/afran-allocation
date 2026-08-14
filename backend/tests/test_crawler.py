from __future__ import annotations

from urllib.parse import unquote

import httpx
import pytest

from app.config import Settings
from app.crawlers.fipiran import FipiranCrawler


@pytest.mark.asyncio
async def test_http_crawler_completes_without_browser_or_crash(fixture_json) -> None:
    responses = {
        "/services/fund/fundtype": fixture_json("fund_types.json"),
        "/services/fund/fundcompare": fixture_json("fund_compare.json"),
        "/services/fund/getfund": fixture_json("fund_detail.json"),
        "/services/chart/getfundchart": fixture_json("nav_history.json"),
        "/services/chart/getfundnetassetchart": fixture_json("net_asset_history.json"),
        "/services/chart/portfoliochart": fixture_json("portfolio_history.json"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = unquote(request.url.path.rstrip("/"))
        if path == "/mf/list":
            return httpx.Response(
                200,
                text="<html><script>fetch('/services/fund/fundcompare')</script></html>",
                headers={"content-type": "text/html"},
            )
        if path in responses:
            return httpx.Response(200, json=responses[path])
        return httpx.Response(404, json={"detail": f"unmocked {path}"})

    settings = Settings(
        database_url="sqlite:///:memory:",
        scheduler_enabled=False,
        playwright_enabled=False,
        http_retries=0,
        crawl_max_rps=20,
    )
    crawler = FipiranCrawler(settings, transport=httpx.MockTransport(handler))
    result = await crawler.crawl()
    assert result.method == "api"
    assert len(result.funds) == 1
    assert len(result.navs) == 2
    assert len(result.performances) == 1
    assert len(result.managers) == 3
    assert len(result.exposures) == 2
    assert result.exposures[-1].equity_exposure is not None
    assert result.diagnostics["complete_equity_exposures_received"] == 1
    assert result.diagnostics["html_probe"]["has_javascript"] is True

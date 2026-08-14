from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx

from app.config import Settings
from app.crawlers.base import BaseCrawler, CrawlerError
from app.crawlers.parser import DataParser
from app.crawlers.app_types import CrawlResult, ExposureRecord, NAVRecord
from app.utils.rate_limit import AsyncRateLimiter

logger = logging.getLogger(__name__)
FetchJSON = Callable[[str, str, dict[str, Any] | None], Awaitable[Any]]


class FipiranCrawler(BaseCrawler):
    """Fipiran adapter with HTTP API first and browser-session fallback."""

    source_name = "fipiran"

    def __init__(
        self,
        settings: Settings,
        *,
        parser: DataParser | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.parser = parser or DataParser()
        self.transport = transport
        self.rate_limiter = AsyncRateLimiter(settings.crawl_max_rps)
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7",
            "Referer": f"{settings.fipiran_url}/",
            "User-Agent": settings.user_agent,
        }

    def _page_url(self) -> str:
        return urljoin(f"{self.settings.fipiran_url}/", self.settings.fipiran_fund_list_page.lstrip("/"))

    def _service_url(self, path: str) -> str:
        root = "/".join(
            [self.settings.fipiran_services_path.strip("/"), path.lstrip("/")]
        )
        return urljoin(f"{self.settings.fipiran_url}/", root)

    async def probe(self) -> dict[str, Any]:
        """Inspect HTML first, as required, without assuming an API response."""
        timeout = httpx.Timeout(self.settings.http_timeout)
        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=timeout,
            follow_redirects=True,
            transport=self.transport,
        ) as client:
            await self.rate_limiter.wait()
            response = await client.get(self._page_url())
            response.raise_for_status()
            body = response.text
            lowered = body.lower()
            return {
                "dns_https_reachable": True,
                "http_status": response.status_code,
                "final_url": str(response.url),
                "content_type": response.headers.get("content-type"),
                "html_bytes": len(response.content),
                "has_javascript": "<script" in lowered,
                "has_xhr_markers": any(
                    marker in lowered for marker in ("/services/", "fetch(", "xmlhttprequest", "axios")
                ),
            }

    async def crawl(self) -> CrawlResult:
        diagnostics: dict[str, Any] = {}
        try:
            diagnostics["html_probe"] = await self.probe()
        except Exception as exc:  # API may still work even if the public page is protected.
            diagnostics["html_probe"] = {"ok": False, "error": self._safe_error(exc)}

        try:
            result = await self._crawl_with_http()
            result.diagnostics = {**diagnostics, **result.diagnostics}
            return result
        except Exception as api_exc:
            diagnostics["api_error"] = self._safe_error(api_exc)
            logger.warning("Fipiran HTTP extraction failed: %s", api_exc)
            if not self.settings.playwright_enabled:
                raise CrawlerError(f"HTTP extraction failed: {self._safe_error(api_exc)}") from api_exc

        try:
            result = await self._crawl_with_playwright()
            result.diagnostics = {**diagnostics, **result.diagnostics}
            return result
        except Exception as browser_exc:
            diagnostics["playwright_error"] = self._safe_error(browser_exc)
            raise CrawlerError(
                "Both Fipiran extraction methods failed; "
                f"http={diagnostics.get('api_error')}; "
                f"playwright={diagnostics.get('playwright_error')}"
            ) from browser_exc

    async def _crawl_with_http(self) -> CrawlResult:
        timeout = httpx.Timeout(self.settings.http_timeout)
        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=timeout,
            follow_redirects=True,
            transport=self.transport,
        ) as client:

            async def fetch(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
                url = self._service_url(path)
                return await self._request_http_json(client, method, url, payload)

            return await self._collect(fetch, method="api")

    async def _request_http_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        payload: dict[str, Any] | None,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.settings.http_retries + 1):
            try:
                await self.rate_limiter.wait()
                response = await client.request(method, url, json=payload)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= self.settings.http_retries:
                    break
                await asyncio.sleep(self.settings.retry_base_delay * (2**attempt))
        raise CrawlerError(f"Request failed for {url}: {self._safe_error(last_error)}")

    async def _crawl_with_playwright(self) -> CrawlResult:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - image includes Playwright.
            raise CrawlerError("Playwright is not installed") from exc

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.settings.user_agent,
                locale="fa-IR",
            )
            page = await context.new_page()
            page.set_default_timeout(self.settings.browser_timeout_ms)
            try:
                response = await page.goto(self._page_url(), wait_until="domcontentloaded")
                if response is None or response.status >= 400:
                    status = response.status if response else "no-response"
                    raise CrawlerError(f"Fipiran page failed in Playwright: {status}")

                async def fetch(
                    method: str, path: str, payload: dict[str, Any] | None = None
                ) -> Any:
                    await self.rate_limiter.wait()
                    url = self._service_url(path)
                    if method.upper() == "POST":
                        api_response = await context.request.post(
                            url, headers=self.headers, data=payload
                        )
                    else:
                        api_response = await context.request.get(url, headers=self.headers)
                    if not api_response.ok:
                        raise CrawlerError(
                            f"Playwright request failed: {api_response.status} {url}"
                        )
                    return await api_response.json()

                result = await self._collect(fetch, method="playwright")
                result.diagnostics["browser_page_status"] = response.status
                return result
            finally:
                await context.close()
                await browser.close()

    async def _collect(self, fetch: FetchJSON, *, method: str) -> CrawlResult:
        errors: list[str] = []
        fund_types: dict[str, str] = {}
        try:
            types_payload = await fetch("GET", self.settings.fipiran_fund_types_path, None)
            fund_types = self.parser.parse_fund_types(types_payload)
        except Exception as exc:
            errors.append(f"fund_types: {self._safe_error(exc)}")

        list_payload = await fetch(
            "POST",
            self.settings.fipiran_fund_compare_path,
            {"regNos": [], "showMarketMakers": False},
        )
        funds = self.parser.parse_fund_list(list_payload, fund_types)
        if not funds:
            raise CrawlerError("Fipiran returned no valid fund records")
        if self.settings.crawl_max_funds:
            funds = funds[: self.settings.crawl_max_funds]

        semaphore = asyncio.Semaphore(self.settings.crawl_detail_concurrency)

        async def collect_one(
            index: int,
        ) -> tuple[int, list[NAVRecord], list[ExposureRecord]]:
            fund = funds[index]
            nav_groups: list[list[NAVRecord]] = []
            exposure_groups: list[list[ExposureRecord]] = []
            async with semaphore:
                query = urlencode({"regno": fund.external_id})
                try:
                    detail = await fetch(
                        "GET", f"{self.settings.fipiran_fund_detail_path}?{query}", None
                    )
                    funds[index] = self.parser.enrich_fund(fund, detail)
                    fund = funds[index]
                except Exception as exc:
                    errors.append(f"fund {fund.external_id} detail: {self._safe_error(exc)}")

                current_nav = self.parser.parse_current_nav(fund)
                if current_nav:
                    nav_groups.append([current_nav])
                current_exposure = self.parser.parse_current_exposure(fund)
                if current_exposure:
                    exposure_groups.append([current_exposure])

                if self.settings.crawl_fetch_history:
                    history_query = urlencode(
                        {
                            "regno": fund.external_id,
                            "showAll": str(self.settings.fipiran_show_all_history).lower(),
                        }
                    )
                    try:
                        nav_payload = await fetch(
                            "GET", f"{self.settings.fipiran_nav_history_path}?{history_query}", None
                        )
                        nav_groups.append(
                            self.parser.parse_nav_history(fund.external_id, nav_payload)
                        )
                    except Exception as exc:
                        errors.append(f"fund {fund.external_id} nav: {self._safe_error(exc)}")
                    try:
                        asset_payload = await fetch(
                            "GET",
                            f"{self.settings.fipiran_net_asset_history_path}?{history_query}",
                            None,
                        )
                        nav_groups.append(
                            self.parser.parse_net_asset_history(fund.external_id, asset_payload)
                        )
                    except Exception as exc:
                        errors.append(f"fund {fund.external_id} assets: {self._safe_error(exc)}")
                if self.settings.crawl_fetch_portfolio_history:
                    portfolio_query = urlencode({"regno": fund.external_id})
                    try:
                        portfolio_payload = await fetch(
                            "GET",
                            f"{self.settings.fipiran_portfolio_history_path}?{portfolio_query}",
                            None,
                        )
                        exposure_groups.insert(
                            0,
                            self.parser.parse_portfolio_history(
                                fund.external_id, portfolio_payload
                            ),
                        )
                    except Exception as exc:
                        errors.append(
                            f"fund {fund.external_id} portfolio: {self._safe_error(exc)}"
                        )
            return (
                index,
                self.parser.merge_nav_records(nav_groups),
                self.parser.merge_exposure_records(exposure_groups),
            )

        collected = await asyncio.gather(*(collect_one(i) for i in range(len(funds))))
        navs = [nav for _, group, _ in collected for nav in group]
        exposures = [exposure for _, _, group in collected for exposure in group]
        for exposure in exposures:
            exposure.source = f"fipiran-{method}"
        performances = [
            record for fund in funds if (record := self.parser.parse_performance(fund)) is not None
        ]
        managers = [record for fund in funds for record in self.parser.parse_managers(fund)]
        return CrawlResult(
            method=method,
            funds=funds,
            navs=navs,
            performances=performances,
            managers=managers,
            exposures=exposures,
            errors=errors,
            diagnostics={
                "fund_types_received": len(fund_types),
                "funds_received": len(funds),
                "nav_records_received": len(navs),
                "management_records_received": len(managers),
                "exposure_records_received": len(exposures),
                "complete_equity_exposures_received": sum(
                    row.equity_exposure is not None for row in exposures
                ),
            },
        )

    @staticmethod
    def _safe_error(error: object) -> str:
        text = str(error) if error is not None else "unknown error"
        return text.replace("\n", " ")[:1000]

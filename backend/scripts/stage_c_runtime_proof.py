#!/usr/bin/env python3
"""Prove Stage C end-to-end from inside the running production container.

This script does not contain fixtures or fallback data.  It fails unless DNS,
Fipiran HTTPS, a real crawl, database persistence and the public FastAPI read
endpoints all succeed.
"""

from __future__ import annotations

import asyncio
import json
import socket
from typing import Any

import httpx

from app.config import get_settings
from app.crawlers.fipiran import FipiranCrawler


async def main() -> None:
    settings = get_settings()
    host = "www.fipiran.com"
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443)})
    probe = await FipiranCrawler(settings).probe()

    headers = {"X-API-Key": settings.crawl_api_key} if settings.crawl_api_key else {}
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:80",
        timeout=httpx.Timeout(240),
    ) as client:
        health = await client.get("/health")
        health.raise_for_status()
        crawl = await client.post("/api/v1/crawl?wait=true", headers=headers)
        crawl.raise_for_status()
        funds = await client.get("/api/v1/funds", params={"limit": 200})
        funds.raise_for_status()
        items = funds.json().get("items", [])
        observed = next(
            (item for item in items if item.get("latest_exposure") is not None),
            None,
        )
        if observed is None:
            raise RuntimeError("No real persisted FundExposure was returned by /api/v1/funds")
        fund_id = observed["id"]
        exposure = await client.get(f"/api/v1/funds/{fund_id}/exposure")
        exposure.raise_for_status()
        ranking = await client.get("/api/v1/exposure/ranking")
        ranking.raise_for_status()

    output: dict[str, Any] = {
        "dns": {"host": host, "addresses": addresses},
        "fipiran_probe": probe,
        "health": health.json(),
        "crawl": crawl.json(),
        "real_api_sample": exposure.json(),
        "ranking_summary": {
            key: ranking.json()[key]
            for key in (
                "benchmark_bm",
                "total_funds",
                "ranked_funds",
                "missing_exposure_funds",
            )
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Run inside the target container to prove one real Fipiran extraction."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from app.config import get_settings
from app.crawlers.fipiran import FipiranCrawler


async def main() -> None:
    settings = get_settings().model_copy(
        update={
            "crawl_max_funds": 1,
            "crawl_fetch_history": False,
            "crawl_fetch_portfolio_history": True,
        }
    )
    crawler = FipiranCrawler(settings)
    probe = await crawler.probe()
    result = await crawler.crawl()
    output = {
        "probe": probe,
        "method": result.method,
        "fund_count": len(result.funds),
        "first_real_fund": asdict(result.funds[0]) if result.funds else None,
        "first_real_exposure": asdict(result.exposures[0]) if result.exposures else None,
        "errors": result.errors,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

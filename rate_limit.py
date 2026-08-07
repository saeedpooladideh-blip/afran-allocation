from __future__ import annotations

import asyncio
import time


class AsyncRateLimiter:
    """Process-local request pacing for polite upstream access."""

    def __init__(self, requests_per_second: float) -> None:
        self._minimum_interval = 1.0 / requests_per_second
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            remaining = self._minimum_interval - (now - self._last_request)
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_request = time.monotonic()

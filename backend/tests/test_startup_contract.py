from __future__ import annotations

import os
import subprocess
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
STARTUP_SCRIPT = BACKEND_ROOT / "scripts/start.sh"


def required_environment() -> dict[str, str]:
    return {
        "PATH": os.environ["PATH"],
        "DATABASE_URL": "sqlite:////tmp/afran-startup-contract.db",
        "FIPIRAN_URL": "https://www.fipiran.com",
        "ALLOCATION_BENCHMARK_BM": "2.99",
        "LOG_LEVEL": "INFO",
        "CRAWL_INTERVAL": "86400",
    }


def test_startup_requires_crawl_api_key() -> None:
    result = subprocess.run(
        ["sh", str(STARTUP_SCRIPT)],
        cwd=BACKEND_ROOT,
        env=required_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "CRAWL_API_KEY is required" in result.stderr


def test_scheduler_true_variants_reject_multiple_workers() -> None:
    for value in ("true", "TRUE", "yes", "on", "Y", "t", "1"):
        result = subprocess.run(
            ["sh", str(STARTUP_SCRIPT)],
            cwd=BACKEND_ROOT,
            env={
                **required_environment(),
                "CRAWL_API_KEY": "test-only-value",
                "SCHEDULER_ENABLED": value,
                "WEB_CONCURRENCY": "2",
            },
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 64
        assert "prevent duplicate crawls" in result.stderr

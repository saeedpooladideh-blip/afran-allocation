from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from decimal import Decimal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application configuration.

    All extraction details are configurable because Fipiran's internal routes
    are not a public, versioned API and can change without notice.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Afran Allocation"
    app_version: str = "1.1.0"
    environment: str = "production"
    database_url: str = "sqlite:////data/afran.db"
    database_auto_create: bool = True
    log_level: str = "INFO"

    fipiran_url: str = "https://www.fipiran.com"
    fipiran_fund_list_page: str = "/mf/list"
    fipiran_services_path: str = "/services"
    fipiran_fund_compare_path: str = "/fund/fundcompare/"
    fipiran_fund_detail_path: str = "/fund/getfund"
    fipiran_fund_types_path: str = "/fund/fundtype"
    fipiran_nav_history_path: str = "/chart/getfundchart"
    fipiran_net_asset_history_path: str = "/chart/getfundnetassetchart"
    fipiran_portfolio_history_path: str = "/chart/portfoliochart"

    http_timeout: float = Field(default=30.0, gt=0, le=120)
    http_retries: int = Field(default=3, ge=0, le=10)
    retry_base_delay: float = Field(default=1.0, ge=0.1, le=30)
    crawl_max_rps: float = Field(default=2.0, gt=0, le=20)
    crawl_detail_concurrency: int = Field(default=4, ge=1, le=20)
    crawl_max_funds: int = Field(default=0, ge=0)
    crawl_fetch_history: bool = True
    crawl_fetch_portfolio_history: bool = True
    fipiran_show_all_history: bool = False
    playwright_enabled: bool = True
    browser_timeout_ms: int = Field(default=45_000, ge=5_000, le=180_000)
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0 Safari/537.36 "
        "AfranAllocation/1.0"
    )

    crawl_interval: int = Field(default=86_400, ge=60)
    scheduler_enabled: bool = True
    crawl_on_startup: bool = False
    crawl_api_key: str | None = None
    allocation_benchmark_bm: Decimal = Field(default=Decimal("2.99"), ge=0, le=100)

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DATABASE_URL must not be empty")
        # SQLAlchemy 2 works with both SQLite now and PostgreSQL later.
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("fipiran_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    def ensure_sqlite_directory(self) -> None:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return
        raw_path = self.database_url.removeprefix(prefix)
        if raw_path == ":memory:" or not raw_path:
            return
        Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

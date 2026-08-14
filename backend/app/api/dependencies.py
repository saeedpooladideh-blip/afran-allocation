from __future__ import annotations

from collections.abc import Generator
from secrets import compare_digest

from fastapi import Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.services.crawl_service import CrawlService


def get_db(request: Request) -> Generator[Session, None, None]:
    with request.app.state.database.session_factory() as session:
        yield session


def get_crawl_service(request: Request) -> CrawlService:
    return request.app.state.crawl_service


def authorize_crawl(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    expected = request.app.state.settings.crawl_api_key
    if expected and (x_api_key is None or not compare_digest(x_api_key, expected)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid X-API-Key header is required",
        )

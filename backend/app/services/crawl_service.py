from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.crawlers.base import BaseCrawler
from app.crawlers.app_types import CrawlResult
from app.models import CrawlLog, Fund, FundExposure, FundManager, FundNAV, FundPerformance

logger = logging.getLogger(__name__)


class CrawlAlreadyRunning(RuntimeError):
    pass


class CrawlService:
    """Orchestrates extraction, validation and append-only persistence."""

    def __init__(
        self,
        crawler: BaseCrawler,
        session_factory: sessionmaker[Session],
        source_url: str,
    ) -> None:
        self.crawler = crawler
        self.session_factory = session_factory
        self.source_url = source_url
        self._lock = asyncio.Lock()
        self._scheduled = False
        self._background_task: asyncio.Task[dict[str, Any]] | None = None
        self.last_runtime_error: str | None = None

    @property
    def is_running(self) -> bool:
        return self._lock.locked() or self._scheduled

    def trigger(self) -> asyncio.Task[dict[str, Any]]:
        if self.is_running:
            raise CrawlAlreadyRunning("A crawl is already running")
        self._scheduled = True
        self._background_task = asyncio.create_task(self.run(), name="fipiran-manual-crawl")
        self._background_task.add_done_callback(self._consume_background_result)
        return self._background_task

    def _consume_background_result(self, task: asyncio.Task[dict[str, Any]]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            return
        except Exception as exc:  # failure is already stored in CrawlLog.
            logger.error("Background crawl failed: %s", exc)

    async def run(self) -> dict[str, Any]:
        if self._lock.locked():
            raise CrawlAlreadyRunning("A crawl is already running")
        async with self._lock:
            self._scheduled = False
            started = datetime.now(UTC)
            started_monotonic = time.monotonic()
            with self.session_factory() as session:
                log = CrawlLog(
                    started_at=started,
                    status="running",
                    source_url=self.source_url,
                )
                session.add(log)
                session.commit()
                session.refresh(log)
                crawl_id = log.id

            try:
                result = await self.crawler.crawl()
                if not result.funds:
                    raise RuntimeError("Crawler produced zero valid funds")
                counts = self._persist_result(result)
                duration_ms = int((time.monotonic() - started_monotonic) * 1000)
                status = "partial" if result.errors else "success"
                with self.session_factory() as session:
                    log = session.get(CrawlLog, crawl_id)
                    if log is None:
                        raise RuntimeError("Crawl log disappeared during persistence")
                    log.finished_at = datetime.now(UTC)
                    log.status = status
                    log.method = result.method
                    log.records_received = result.record_count
                    log.funds_inserted = counts["funds_inserted"]
                    log.funds_updated = counts["funds_updated"]
                    log.navs_inserted = counts["navs_inserted"]
                    log.performances_inserted = counts["performances_inserted"]
                    log.managers_upserted = counts["managers_upserted"]
                    log.exposures_inserted = counts["exposures_inserted"]
                    log.error_count = len(result.errors)
                    log.error_message = " | ".join(result.errors)[:8000] or None
                    log.duration_ms = duration_ms
                    log.diagnostics = result.diagnostics
                    session.commit()
                self.last_runtime_error = None
                logger.info(
                    "Crawl completed",
                    extra={
                        "crawl_id": crawl_id,
                        "method": result.method,
                        "record_count": result.record_count,
                        "duration_ms": duration_ms,
                    },
                )
                return {
                    "crawl_id": crawl_id,
                    "status": status,
                    "method": result.method,
                    "records_received": result.record_count,
                    **counts,
                    "error_count": len(result.errors),
                    "duration_ms": duration_ms,
                }
            except Exception as exc:
                duration_ms = int((time.monotonic() - started_monotonic) * 1000)
                error_message = self._safe_error(exc)
                self.last_runtime_error = error_message
                with self.session_factory() as session:
                    log = session.get(CrawlLog, crawl_id)
                    if log is not None:
                        log.finished_at = datetime.now(UTC)
                        log.status = "failed"
                        log.error_count = 1
                        log.error_message = error_message
                        log.duration_ms = duration_ms
                        session.commit()
                logger.exception(
                    "Crawl failed",
                    extra={"crawl_id": crawl_id, "duration_ms": duration_ms},
                )
                raise

    def _persist_result(self, result: CrawlResult) -> dict[str, int]:
        now = datetime.now(UTC)
        counts = {
            "funds_inserted": 0,
            "funds_updated": 0,
            "navs_inserted": 0,
            "performances_inserted": 0,
            "managers_upserted": 0,
            "exposures_inserted": 0,
        }
        external_ids = {record.external_id for record in result.funds}
        with self.session_factory() as session:
            existing = {
                fund.external_id: fund
                for fund in session.scalars(
                    select(Fund).where(Fund.external_id.in_(external_ids))
                ).all()
            }
            for record in result.funds:
                values = asdict(record)
                values.pop("external_id")
                values["last_seen_at"] = now
                fund = existing.get(record.external_id)
                if fund is None:
                    fund = Fund(external_id=record.external_id, first_seen_at=now, **values)
                    session.add(fund)
                    session.flush()
                    existing[record.external_id] = fund
                    counts["funds_inserted"] += 1
                else:
                    for key, value in values.items():
                        setattr(fund, key, value)
                    counts["funds_updated"] += 1

            fund_ids = {key: value.id for key, value in existing.items() if key in external_ids}
            self._insert_navs(session, result, fund_ids, counts)
            self._insert_performance(session, result, fund_ids, counts)
            self._upsert_managers(session, result, fund_ids, counts, now)
            self._insert_exposures(session, result, fund_ids, counts)
            session.commit()
        return counts

    @staticmethod
    def _insert_navs(
        session: Session,
        result: CrawlResult,
        fund_ids: dict[str, int],
        counts: dict[str, int],
    ) -> None:
        keys = {(fund_ids[record.external_id], record.nav_date) for record in result.navs if record.external_id in fund_ids}
        existing_keys: set[tuple[int, str]] = set()
        if keys:
            ids = {fund_id for fund_id, _ in keys}
            dates = {date for _, date in keys}
            existing_keys = set(
                session.execute(
                    select(FundNAV.fund_id, FundNAV.nav_date).where(
                        FundNAV.fund_id.in_(ids), FundNAV.nav_date.in_(dates)
                    )
                ).all()
            )
        for record in result.navs:
            fund_id = fund_ids.get(record.external_id)
            if fund_id is None or (fund_id, record.nav_date) in existing_keys:
                continue
            values = asdict(record)
            values.pop("external_id")
            session.add(FundNAV(fund_id=fund_id, **values))
            existing_keys.add((fund_id, record.nav_date))
            counts["navs_inserted"] += 1

    @staticmethod
    def _insert_performance(
        session: Session,
        result: CrawlResult,
        fund_ids: dict[str, int],
        counts: dict[str, int],
    ) -> None:
        keys = {
            (fund_ids[record.external_id], record.as_of_date)
            for record in result.performances
            if record.external_id in fund_ids
        }
        existing_keys: set[tuple[int, str]] = set()
        if keys:
            ids = {fund_id for fund_id, _ in keys}
            dates = {date for _, date in keys}
            existing_keys = set(
                session.execute(
                    select(FundPerformance.fund_id, FundPerformance.as_of_date).where(
                        FundPerformance.fund_id.in_(ids),
                        FundPerformance.as_of_date.in_(dates),
                    )
                ).all()
            )
        for record in result.performances:
            fund_id = fund_ids.get(record.external_id)
            if fund_id is None or (fund_id, record.as_of_date) in existing_keys:
                continue
            values = asdict(record)
            values.pop("external_id")
            session.add(FundPerformance(fund_id=fund_id, **values))
            existing_keys.add((fund_id, record.as_of_date))
            counts["performances_inserted"] += 1

    @staticmethod
    def _upsert_managers(
        session: Session,
        result: CrawlResult,
        fund_ids: dict[str, int],
        counts: dict[str, int],
        now: datetime,
    ) -> None:
        for record in result.managers:
            fund_id = fund_ids.get(record.external_id)
            if fund_id is None:
                continue
            manager = session.scalar(
                select(FundManager).where(
                    FundManager.fund_id == fund_id,
                    FundManager.role == record.role,
                    FundManager.name == record.name,
                )
            )
            if manager is None:
                manager = FundManager(
                    fund_id=fund_id,
                    role=record.role,
                    name=record.name,
                    external_id=record.manager_external_id,
                    raw_data=record.raw_data,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(manager)
            else:
                manager.external_id = record.manager_external_id
                manager.raw_data = record.raw_data
                manager.last_seen_at = now
            counts["managers_upserted"] += 1

    @staticmethod
    def _insert_exposures(
        session: Session,
        result: CrawlResult,
        fund_ids: dict[str, int],
        counts: dict[str, int],
    ) -> None:
        keys = {
            (fund_ids[record.external_id], record.report_date)
            for record in result.exposures
            if record.external_id in fund_ids
        }
        existing_keys: set[tuple[int, str]] = set()
        if keys:
            ids = {fund_id for fund_id, _ in keys}
            dates = {date for _, date in keys}
            existing_keys = set(
                session.execute(
                    select(FundExposure.fund_id, FundExposure.report_date).where(
                        FundExposure.fund_id.in_(ids),
                        FundExposure.report_date.in_(dates),
                    )
                ).all()
            )
        for record in result.exposures:
            fund_id = fund_ids.get(record.external_id)
            if fund_id is None or (fund_id, record.report_date) in existing_keys:
                continue
            values = asdict(record)
            values.pop("external_id")
            session.add(FundExposure(fund_id=fund_id, **values))
            existing_keys.add((fund_id, record.report_date))
            counts["exposures_inserted"] += 1

    @staticmethod
    def _safe_error(error: object) -> str:
        return str(error).replace("\n", " ")[:8000]

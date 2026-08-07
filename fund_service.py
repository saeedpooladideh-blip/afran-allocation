from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import CrawlLog, Fund, FundExposure, FundManager, FundNAV, FundPerformance


class FundService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_funds(
        self,
        *,
        offset: int,
        limit: int,
        query: str | None,
        fund_type: str | None,
    ) -> tuple[int, list[Fund]]:
        filters = []
        if query:
            pattern = f"%{query.strip()}%"
            filters.append(or_(Fund.name.ilike(pattern), Fund.symbol.ilike(pattern)))
        if fund_type:
            pattern = f"%{fund_type.strip()}%"
            filters.append(
                or_(Fund.fund_type_name.ilike(pattern), Fund.fund_type_code == fund_type.strip())
            )
        total = self.session.scalar(select(func.count(Fund.id)).where(*filters)) or 0
        funds = self.session.scalars(
            select(Fund)
            .where(*filters)
            .order_by(Fund.name)
            .offset(offset)
            .limit(limit)
        ).all()
        return total, list(funds)

    def get_fund(self, fund_id: int) -> Fund | None:
        return self.session.scalar(
            select(Fund)
            .where(Fund.id == fund_id)
            .options(selectinload(Fund.managers))
        )

    def latest_nav(self, fund_id: int) -> FundNAV | None:
        return self.session.scalar(
            select(FundNAV)
            .where(FundNAV.fund_id == fund_id)
            .order_by(FundNAV.nav_date.desc(), FundNAV.id.desc())
            .limit(1)
        )

    def latest_performance(self, fund_id: int) -> FundPerformance | None:
        return self.session.scalar(
            select(FundPerformance)
            .where(FundPerformance.fund_id == fund_id)
            .order_by(FundPerformance.as_of_date.desc(), FundPerformance.id.desc())
            .limit(1)
        )

    def latest_exposure(self, fund_id: int) -> FundExposure | None:
        return self.session.scalar(
            select(FundExposure)
            .where(FundExposure.fund_id == fund_id)
            .order_by(FundExposure.report_date.desc(), FundExposure.id.desc())
            .limit(1)
        )

    def latest_exposures(self, fund_ids: list[int]) -> dict[int, FundExposure]:
        if not fund_ids:
            return {}
        rows = self.session.scalars(
            select(FundExposure)
            .where(FundExposure.fund_id.in_(fund_ids))
            .order_by(
                FundExposure.fund_id,
                FundExposure.report_date.desc(),
                FundExposure.id.desc(),
            )
        ).all()
        latest: dict[int, FundExposure] = {}
        for row in rows:
            latest.setdefault(row.fund_id, row)
        return latest

    def exposure_ranking(self) -> tuple[int, int, list[tuple[Fund, FundExposure]]]:
        funds = list(self.session.scalars(select(Fund)).all())
        latest = self.latest_exposures([fund.id for fund in funds])
        complete = [
            (fund, latest[fund.id])
            for fund in funds
            if fund.id in latest and latest[fund.id].equity_exposure is not None
        ]
        complete.sort(key=lambda item: item[1].equity_exposure, reverse=True)
        return len(funds), len(funds) - len(complete), complete

    def nav_history(self, fund_id: int, *, offset: int, limit: int) -> tuple[int, list[FundNAV]]:
        total = self.session.scalar(
            select(func.count(FundNAV.id)).where(FundNAV.fund_id == fund_id)
        ) or 0
        rows = self.session.scalars(
            select(FundNAV)
            .where(FundNAV.fund_id == fund_id)
            .order_by(FundNAV.nav_date.desc(), FundNAV.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return total, list(rows)

    def system_counts(self) -> dict[str, int]:
        return {
            "funds": self.session.scalar(select(func.count(Fund.id))) or 0,
            "nav_records": self.session.scalar(select(func.count(FundNAV.id))) or 0,
            "performance_records": self.session.scalar(select(func.count(FundPerformance.id))) or 0,
            "exposure_records": self.session.scalar(select(func.count(FundExposure.id))) or 0,
            "manager_records": self.session.scalar(select(func.count(FundManager.id))) or 0,
            "crawl_runs": self.session.scalar(select(func.count(CrawlLog.id))) or 0,
        }

    def latest_crawl(self) -> CrawlLog | None:
        return self.session.scalar(select(CrawlLog).order_by(CrawlLog.id.desc()).limit(1))

    def latest_successful_crawl(self) -> CrawlLog | None:
        return self.session.scalar(
            select(CrawlLog)
            .where(CrawlLog.status.in_(["success", "partial"]))
            .order_by(CrawlLog.id.desc())
            .limit(1)
        )

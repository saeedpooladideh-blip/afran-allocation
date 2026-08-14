from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import authorize_crawl, get_crawl_service, get_db
from app.api.schemas import (
    CrawlAccepted,
    CrawlOut,
    ExposureOut,
    ExposureRankingItem,
    ExposureRankingResponse,
    FundDetail,
    FundExposureResponse,
    FundHistoryResponse,
    FundListResponse,
    FundSummary,
    HealthResponse,
    ManagerOut,
    NAVOut,
    PerformanceOut,
    SystemStatus,
)
from app.services.crawl_service import CrawlAlreadyRunning, CrawlService
from app.services.fund_service import FundService

router = APIRouter()


def to_nav(row: object | None) -> NAVOut | None:
    return NAVOut.model_validate(row) if row is not None else None


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> HealthResponse:
    database_status = "connected"
    try:
        db.execute(text("SELECT 1"))
        latest_success = FundService(db).latest_successful_crawl()
    except Exception as exc:
        database_status = "error"
        latest_success = None
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="unhealthy",
            service="Afran Allocation",
            version=request.app.state.settings.app_version,
            database=database_status,
            source="Fipiran",
            details={"database_error": type(exc).__name__},
        )
    return HealthResponse(
        status="healthy",
        service="Afran Allocation",
        version=request.app.state.settings.app_version,
        database=database_status,
        source="Fipiran",
        latest_successful_crawl_at=latest_success.finished_at if latest_success else None,
        details={},
    )


@router.get("/funds", response_model=FundListResponse, tags=["funds"])
def list_funds(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    q: str | None = None,
    fund_type: str | None = None,
) -> FundListResponse:
    service = FundService(db)
    total, funds = service.list_funds(
        offset=offset, limit=limit, query=q, fund_type=fund_type
    )
    latest_exposures = service.latest_exposures([fund.id for fund in funds])
    items = [
        FundSummary(
            **FundSummary.model_validate(fund).model_dump(
                exclude={"latest_nav", "latest_exposure"}
            ),
            latest_nav=to_nav(service.latest_nav(fund.id)),
            latest_exposure=(
                ExposureOut.model_validate(latest_exposures[fund.id])
                if fund.id in latest_exposures
                else None
            ),
        )
        for fund in funds
    ]
    return FundListResponse(total=total, offset=offset, limit=limit, items=items)


@router.get("/funds/{fund_id}", response_model=FundDetail, tags=["funds"])
def fund_detail(fund_id: int, db: Annotated[Session, Depends(get_db)]) -> FundDetail:
    service = FundService(db)
    fund = service.get_fund(fund_id)
    if fund is None:
        raise HTTPException(status_code=404, detail="Fund not found")
    return FundDetail(
        **FundDetail.model_validate(fund).model_dump(
            exclude={"latest_nav", "latest_exposure", "latest_performance", "managers"}
        ),
        latest_nav=to_nav(service.latest_nav(fund.id)),
        latest_exposure=(
            ExposureOut.model_validate(row)
            if (row := service.latest_exposure(fund.id)) is not None
            else None
        ),
        latest_performance=(
            PerformanceOut.model_validate(row)
            if (row := service.latest_performance(fund.id)) is not None
            else None
        ),
        managers=[ManagerOut.model_validate(manager) for manager in fund.managers],
    )


@router.get(
    "/funds/{fund_id}/exposure",
    response_model=FundExposureResponse,
    tags=["allocation"],
)
def fund_exposure(
    fund_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> FundExposureResponse:
    service = FundService(db)
    fund = service.get_fund(fund_id)
    if fund is None:
        raise HTTPException(status_code=404, detail="Fund not found")
    latest = service.latest_exposure(fund_id)
    return FundExposureResponse(
        fund_id=fund.id,
        fund_name=fund.name,
        benchmark_bm=request.app.state.settings.allocation_benchmark_bm,
        latest=ExposureOut.model_validate(latest) if latest is not None else None,
    )


@router.get(
    "/exposure/ranking",
    response_model=ExposureRankingResponse,
    tags=["allocation"],
)
def exposure_ranking(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> ExposureRankingResponse:
    total_funds, missing, rows = FundService(db).exposure_ranking()
    return ExposureRankingResponse(
        benchmark_bm=request.app.state.settings.allocation_benchmark_bm,
        total_funds=total_funds,
        ranked_funds=len(rows),
        missing_exposure_funds=missing,
        items=[
            ExposureRankingItem(
                rank=index,
                fund_id=fund.id,
                external_id=fund.external_id,
                name=fund.name,
                symbol=fund.symbol,
                fund_type_name=fund.fund_type_name,
                exposure=ExposureOut.model_validate(exposure),
            )
            for index, (fund, exposure) in enumerate(rows, start=1)
        ],
    )


@router.get("/funds/{fund_id}/history", response_model=FundHistoryResponse, tags=["funds"])
def fund_history(
    fund_id: int,
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=2000)] = 365,
) -> FundHistoryResponse:
    service = FundService(db)
    if service.get_fund(fund_id) is None:
        raise HTTPException(status_code=404, detail="Fund not found")
    total, rows = service.nav_history(fund_id, offset=offset, limit=limit)
    return FundHistoryResponse(
        fund_id=fund_id,
        total=total,
        offset=offset,
        limit=limit,
        items=[NAVOut.model_validate(row) for row in rows],
    )


@router.post(
    "/crawl",
    response_model=CrawlOut | CrawlAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["crawler"],
    dependencies=[Depends(authorize_crawl)],
)
async def start_crawl(
    service: Annotated[CrawlService, Depends(get_crawl_service)],
    wait: bool = Query(default=False, description="Wait for completion instead of queuing"),
) -> CrawlOut | CrawlAccepted:
    try:
        if wait:
            return CrawlOut.model_validate(await service.run())
        service.trigger()
        return CrawlAccepted(message="Crawl queued; inspect /status for progress")
    except CrawlAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Fipiran crawl failed: {str(exc)[:500]}") from exc


@router.get("/status", response_model=SystemStatus, tags=["system"])
def system_status(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CrawlService, Depends(get_crawl_service)],
) -> SystemStatus:
    fund_service = FundService(db)
    return SystemStatus(
        service="Afran Allocation",
        version=request.app.state.settings.app_version,
        database="connected",
        crawler_running=service.is_running,
        scheduler_enabled=request.app.state.settings.scheduler_enabled,
        source="Fipiran",
        counts=fund_service.system_counts(),
        latest_crawl=fund_service.latest_crawl(),
        latest_successful_crawl=fund_service.latest_successful_crawl(),
        last_runtime_error=service.last_runtime_error,
    )

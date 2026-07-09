"""事件日志与统计 REST API 路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.constants import API_PREFIX, DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.extensions import get_db
from src.schema.http.event import (
    EventResponse,
    EventListResponse,
    ExceptionStatsItem,
    TrendItem,
)
from src.service.event_task import (
    list_events,
    get_event,
    stats_by_exception,
    stats_trend,
)


router = APIRouter(prefix="/events", tags=["事件日志"])


def _to_response(obj) -> EventResponse:
    return EventResponse.model_validate(obj)


# ── 查询 ────────────────────────────────────────


@router.get("", response_model=EventListResponse)
def list_all(
    db: Session = Depends(get_db),
    view_id: int | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = list_events(
        db, view_id=view_id, start=start, end=end, page=page, page_size=page_size
    )
    return EventListResponse(
        items=[_to_response(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{id}", response_model=EventResponse)
def get_one(id: int, db: Session = Depends(get_db)):
    obj = get_event(db, id)
    if obj is None:
        raise HTTPException(status_code=404, detail="事件不存在")
    return _to_response(obj)


# ── 统计 ────────────────────────────────────────

stats_router = APIRouter(prefix="/events/stats", tags=["事件统计"])


@stats_router.get("/by-exception", response_model=list[ExceptionStatsItem])
def by_exception(
    db: Session = Depends(get_db),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
):
    rows = stats_by_exception(db, start=start, end=end)
    return [ExceptionStatsItem(**r) for r in rows]


@stats_router.get("/trend", response_model=list[TrendItem])
def trend(
    db: Session = Depends(get_db),
    granularity: str = Query("day", pattern="^(hour|day|month)$"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
):
    rows = stats_trend(db, granularity=granularity, start=start, end=end)
    return [TrendItem(**r) for r in rows]

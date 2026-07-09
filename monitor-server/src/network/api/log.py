"""日志 REST API 路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.extensions import get_db
from src.schema.http.log import LogEntryResponse, LogListResponse, LogStatsItem
from src.service.log_task import query_logs, stats_by_log_type, stats_by_severity

router = APIRouter(prefix="/logs", tags=["日志"])


@router.get("", response_model=LogListResponse)
def list_all(
    db: Session = Depends(get_db),
    log_type: int | None = Query(None),
    operator_id: int | None = Query(None),
    view_id: int | None = Query(None),
    event_id: int | None = Query(None),
    severity: int | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = query_logs(
        db,
        log_type=log_type,
        operator_id=operator_id,
        view_id=view_id,
        event_id=event_id,
        severity=severity,
        start=start,
        end=end,
        page=page,
        page_size=page_size,
    )
    return LogListResponse(
        items=[LogEntryResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=list[LogStatsItem])
def stats(group_by: str = Query("log_type", pattern="^(log_type|severity)$"), db: Session = Depends(get_db)):
    if group_by == "log_type":
        rows = stats_by_log_type(db)
    else:
        rows = stats_by_severity(db)
    return [LogStatsItem(**r) for r in rows]

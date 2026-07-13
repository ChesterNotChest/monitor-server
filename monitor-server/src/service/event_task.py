"""事件查询与统计服务层门户。"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.situation_event import SituationEvent
from src.models.exception import ExceptionDef
from src.repository.situation_event_repo import SituationEventRepo


def _repo(db: Session) -> SituationEventRepo:
    return SituationEventRepo(db)


# ── 查询 ────────────────────────────────────────


def list_events(
    db: Session,
    view_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SituationEvent], int]:
    """分页查询事件，支持按 view 和时间范围过滤，时间倒序。"""
    query = select(SituationEvent).order_by(SituationEvent.timestamp.desc())

    if view_id is not None:
        query = query.where(SituationEvent.view_id == view_id)
    if start is not None:
        query = query.where(SituationEvent.timestamp >= start)
    if end is not None:
        query = query.where(SituationEvent.timestamp <= end)

    total = db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    items = list(
        db.scalars(query.offset((page - 1) * page_size).limit(page_size))
    )

    return items, total


def get_event(db: Session, id: int) -> SituationEvent | None:
    return _repo(db).get(id)


# ── 聚合统计 ────────────────────────────────────


def stats_by_exception(
    db: Session,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    """按异常类型分组统计事件数量。返回 [{exception_id, exception_severity, count}]。"""
    query = (
        select(
            SituationEvent.exception_id,
            ExceptionDef.severity,
            func.count(SituationEvent.id).label("count"),
        )
        .join(ExceptionDef, SituationEvent.exception_id == ExceptionDef.id)
    )

    if start is not None:
        query = query.where(SituationEvent.timestamp >= start)
    if end is not None:
        query = query.where(SituationEvent.timestamp <= end)

    query = query.group_by(SituationEvent.exception_id).order_by(func.count(SituationEvent.id).desc())

    rows = db.execute(query).all()
    return [
        {"exception_id": row.exception_id, "exception_severity": row.severity.name, "count": row.count}
        for row in rows
    ]


def stats_trend(
    db: Session,
    granularity: str = "day",
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    """按时间粒度统计事件趋势。返回 [{period, count}]。

    granularity: "hour" | "day" | "month"（默认 "day"）
    """
    fmt_map = {
        "hour": "%Y-%m-%dT%H",
        "day": "%Y-%m-%d",
        "month": "%Y-%m",
    }
    fmt = fmt_map.get(granularity, "%Y-%m-%d")
    dialect = db.get_bind().dialect.name if db.get_bind() is not None else ""

    if dialect == "mysql":
        period_expr = func.date_format(SituationEvent.timestamp, fmt).label("period")
    else:
        period_expr = func.strftime(fmt, SituationEvent.timestamp).label("period")
    count_expr = func.count(SituationEvent.id).label("count")

    query = select(period_expr, count_expr)

    if start is not None:
        query = query.where(SituationEvent.timestamp >= start)
    if end is not None:
        query = query.where(SituationEvent.timestamp <= end)

    query = query.group_by(period_expr).order_by(period_expr)

    rows = db.execute(query).all()
    return [{"period": row.period, "count": row.count} for row in rows]

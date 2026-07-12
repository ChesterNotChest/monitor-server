"""Report API routes."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.report_schema import (
    DailyReportResponse,
    DeepSeekDailyReportRequest,
    ReportResponse,
)
from src.service import report_task

router = APIRouter(prefix="/reports", tags=["报表"])
_perm = Depends(require_permission("report:view"))


@router.get("/weekly", response_model=ReportResponse)
def weekly_report(db: Session = Depends(get_db), _user=_perm):
    """Get weekly aggregate report."""

    return report_task.get_weekly_report(db)


@router.get("/monthly", response_model=ReportResponse)
def monthly_report(db: Session = Depends(get_db), _user=_perm):
    """Get monthly aggregate report."""

    return report_task.get_monthly_report(db)


@router.get("/daily", response_model=DailyReportResponse)
def daily_report(date: date | None = None, db: Session = Depends(get_db), _user=_perm):
    """Get AI-generated daily monitoring report."""

    return report_task.get_daily_report(db, date)


@router.post("/daily/deepseek", response_model=DailyReportResponse)
def deepseek_daily_report(
    body: DeepSeekDailyReportRequest,
    db: Session = Depends(get_db),
    _user=_perm,
):
    """Generate a daily monitoring report with a user-provided DeepSeek key."""

    if not body.api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DeepSeek API key is required",
        )

    try:
        return report_task.get_deepseek_daily_report(
            db=db,
            api_key=body.api_key,
            target_date=body.date,
            model=body.model,
        )
    except report_task.DeepSeekReportError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

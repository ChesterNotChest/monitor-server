"""Report API routes — 日报/周报/月报 + API Key 管理。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.config import settings
from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.report_schema import (
    DailyReportResponse,
    DeepSeekDailyReportRequest,
    PersistedDailyReportResponse,
    ReportResponse,
    ReportSettingsRequest,
    ReportSettingsResponse,
)
from src.service import report_task
from src.service.schedule_report import generate_now, get_next_scheduled

router = APIRouter(prefix="/reports", tags=["报表"])
_perm = Depends(require_permission("report:view"))


# ── Weekly / Monthly ─────────────────────────────

@router.get("/weekly/", response_model=ReportResponse)
def weekly_report(db: Session = Depends(get_db), _user=_perm):
    """Get weekly aggregate report."""
    return report_task.get_weekly_report(db)


@router.get("/monthly/", response_model=ReportResponse)
def monthly_report(db: Session = Depends(get_db), _user=_perm):
    """Get monthly aggregate report."""
    return report_task.get_monthly_report(db)


# ── Daily (legacy + persisted) ───────────────────

@router.get("/daily/", response_model=DailyReportResponse)
def daily_report(date_param: date | None = None, db: Session = Depends(get_db), _user=_perm):
    """Get AI-generated daily monitoring report (legacy format, backward compat).

    For persisted format with stats+insights, use GET /daily/persisted/?date=YYYY-MM-DD.
    """
    return report_task.get_daily_report(db, date_param)


@router.get("/daily/persisted/", response_model=PersistedDailyReportResponse)
def daily_report_persisted(date: date | None = None, db: Session = Depends(get_db), _user=_perm):
    """Get persisted daily report with stats + insights (new format).

    Returns persisted data if available, otherwise falls back to real-time stats-only.
    """
    import datetime as _dt
    report_date = date or _dt.date.today()

    persisted = report_task.load_daily_report(db, report_date)
    if persisted:
        persisted["next_scheduled_at"] = get_next_scheduled()
        return persisted

    # Fallback: real-time stats only, no insights
    stats = report_task.build_daily_stats(db, report_date)
    next_scheduled_at = get_next_scheduled()
    return {
        "report_date": report_date.isoformat(),
        "stats": stats,
        "insights": None,
        "ai_provider": None,
        "ai_model": None,
        "regenerated_count": 0,
        "generated_at": None,
        "next_scheduled_at": next_scheduled_at,
        "generated_now": False,
    }


@router.post("/daily/generate-now/", response_model=PersistedDailyReportResponse)
async def daily_generate_now(db: Session = Depends(get_db), _user=_perm):
    """Manually trigger instant daily report generation (00:00~now CST). Persists and returns."""
    result = await generate_now()
    if not result:
        raise HTTPException(status_code=500, detail="Report generation failed")
    return result


@router.post("/daily/deepseek/", response_model=DailyReportResponse)
def deepseek_daily_report(
    body: DeepSeekDailyReportRequest,
    db: Session = Depends(get_db),
    _user=_perm,
):
    """Generate a daily monitoring report with a user-provided DeepSeek key (legacy)."""
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


# ── Settings ─────────────────────────────────────

@router.get("/settings/", response_model=ReportSettingsResponse)
def report_settings(db: Session = Depends(get_db), _user=_perm):
    """Get masked API key status and next scheduled generation time."""
    from src.repository.daily_report_repo import ReportSettingRepo

    repo = ReportSettingRepo(db)
    user_key = repo.get_api_key()
    env_key = settings.DEEPSEEK_API_KEY if hasattr(settings, "DEEPSEEK_API_KEY") else ""

    effective_key = user_key or env_key
    model = repo.get_model() or settings.DEEPSEEK_REPORT_MODEL

    key_preview = None
    if effective_key:
        k = effective_key
        if len(k) > 12:
            key_preview = k[:6] + "****" + k[-4:]
        else:
            key_preview = k[:4] + "****"

    return {
        "has_key": bool(effective_key),
        "key_preview": key_preview,
        "model": model,
        "source": "user" if user_key else ("env" if env_key else None),
        "next_scheduled_at": get_next_scheduled(),
    }


@router.put("/settings/", response_model=ReportSettingsResponse)
def update_report_settings(
    body: ReportSettingsRequest,
    db: Session = Depends(get_db),
    _user=_perm,
):
    """Save user API key override. Empty key clears the override."""
    from src.repository.daily_report_repo import ReportSettingRepo

    repo = ReportSettingRepo(db)
    if body.api_key is not None and body.api_key.strip():
        repo.set_api_key(body.api_key.strip(), body.model)
    elif body.api_key is not None and not body.api_key.strip():
        # Clear override
        repo.set_api_key("", None)
    db.commit()

    return report_settings(db)

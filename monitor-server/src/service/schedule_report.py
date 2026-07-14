"""Report scheduler — 日报定时生成 (17:00 CST) + 凌晨补充 (00:05 CST)。

集成方式：在 app.py startup 中调用 schedule_report.init_scheduler()。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import settings
from src.extensions import SessionLocal

logger = logging.getLogger(__name__)

# Beijing timezone
_CST = timezone(timedelta(hours=8))

_scheduler: AsyncIOScheduler | None = None


def _cst_now() -> datetime:
    """Current time in CST."""
    return datetime.now(_CST)


def _cst_today() -> date:
    return _cst_now().date()


def _cst_yesterday() -> date:
    return _cst_today() - timedelta(days=1)


def _next_scheduled_cst() -> str:
    """Return next 17:00 CST as ISO string (for frontend display)."""
    now = _cst_now()
    scheduled = datetime(now.year, now.month, now.day, 17, 0, 0, tzinfo=_CST)
    if now >= scheduled:
        scheduled += timedelta(days=1)
    return scheduled.strftime("%Y-%m-%d %H:%M CST")


# ── Scheduled jobs ────────────────────────────────


async def _generate_17h_report() -> None:
    """17:00 CST: generate today's report (00:00~17:00)."""
    today = _cst_today()
    logger.info("[Scheduler] 17:00 trigger — generating report for %s", today)

    db = SessionLocal()
    try:
        from src.service.report_task import build_daily_stats, save_daily_report
        from src.service.report_task import generate_insights, build_event_context

        stats = build_daily_stats(db, today, time_start=time.min, time_end=time(17, 0))
        save_daily_report(db, today, stats)

        # AI insights (if API key configured)
        api_key = _get_api_key(db)
        if api_key:
            try:
                ctx = build_event_context(db, today, time_start=time.min, time_end=time(17, 0))
                import asyncio
                insights = await generate_insights(db, today, api_key,
                                                   model=settings.DEEPSEEK_REPORT_MODEL)
                # Re-save with insights
                save_daily_report(db, today, stats, insights_json=insights,
                                  ai_provider="deepseek",
                                  ai_model=settings.DEEPSEEK_REPORT_MODEL)
            except Exception:
                logger.exception("[Scheduler] AI insights failed for %s", today)
    except Exception:
        logger.exception("[Scheduler] 17:00 report generation failed for %s", today)
    finally:
        db.close()


async def _generate_supplement() -> None:
    """00:05 CST: supplement yesterday's remainder (17:00~23:59) + regenerate insights."""
    yesterday = _cst_yesterday()
    logger.info("[Scheduler] 00:05 supplement — regenerating full day for %s", yesterday)

    db = SessionLocal()
    try:
        from src.service.report_task import build_daily_stats, save_daily_report
        from src.service.report_task import generate_insights

        # Full day stats (00:00~23:59)
        stats = build_daily_stats(db, yesterday, time_start=time.min, time_end=time(23, 59, 59))
        api_key = _get_api_key(db)

        insights = None
        ai_provider = None
        ai_model = None
        if api_key:
            try:
                insights = await generate_insights(db, yesterday, api_key,
                                                   model=settings.DEEPSEEK_REPORT_MODEL)
                ai_provider = "deepseek"
                ai_model = settings.DEEPSEEK_REPORT_MODEL
            except Exception:
                logger.exception("[Scheduler] Supplement AI insights failed for %s", yesterday)

        save_daily_report(db, yesterday, stats, insights_json=insights,
                          ai_provider=ai_provider, ai_model=ai_model)
    except Exception:
        logger.exception("[Scheduler] Supplement generation failed for %s", yesterday)
    finally:
        db.close()


async def generate_now() -> dict:
    """Manual instant generation: 00:00~now CST, persist and return."""
    today = _cst_today()
    now = _cst_now().time()

    db = SessionLocal()
    try:
        from src.service.report_task import build_daily_stats, save_daily_report, load_daily_report
        from src.service.report_task import generate_insights

        stats = build_daily_stats(db, today, time_start=time.min, time_end=now)
        api_key = _get_api_key(db)

        insights = None
        ai_provider = None
        ai_model = None
        if api_key:
            try:
                insights = await generate_insights(db, today, api_key,
                                                   model=settings.DEEPSEEK_REPORT_MODEL)
                ai_provider = "deepseek"
                ai_model = settings.DEEPSEEK_REPORT_MODEL
            except Exception:
                logger.exception("[Manual] AI insights failed for %s", today)

        save_daily_report(db, today, stats, insights_json=insights,
                          ai_provider=ai_provider, ai_model=ai_model)
        result = load_daily_report(db, today)
        if result:
            result["generated_now"] = True
            result["next_scheduled_at"] = _next_scheduled_cst()
        return result or {"error": "Failed to load report after save"}
    finally:
        db.close()


async def _startup_backfill() -> None:
    """Check for missing today's report on startup and backfill if needed."""
    today = _cst_today()
    db = SessionLocal()
    try:
        from src.models.daily_report import DailyReport
        from sqlalchemy import select
        existing = db.scalar(select(DailyReport).where(DailyReport.report_date == today))
        if existing:
            logger.info("[Scheduler] Startup backfill: report for %s already exists, skipping", today)
            return
        logger.info("[Scheduler] Startup backfill: generating missing report for %s", today)
    finally:
        db.close()

    await _generate_17h_report()


def _get_api_key(db) -> str | None:
    """API key resolution: user override > env default > None."""
    from src.repository.daily_report_repo import ReportSettingRepo
    repo = ReportSettingRepo(db)
    user_key = repo.get_api_key()
    if user_key:
        return user_key
    env_key = getattr(settings, "DEEPSEEK_API_KEY", None)
    return env_key or None


# ── Init ──────────────────────────────────────────


def init_scheduler() -> None:
    """Register cron jobs and start the APScheduler. Call from app.py startup."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    # Job 1: 17:00 CST daily
    _scheduler.add_job(
        _generate_17h_report,
        trigger=CronTrigger(hour=17, minute=0, timezone="Asia/Shanghai"),
        id="report-daily-1700",
        name="Daily report 17:00 CST",
        replace_existing=True,
    )

    # Job 2: 00:05 CST supplement
    _scheduler.add_job(
        _generate_supplement,
        trigger=CronTrigger(hour=0, minute=5, timezone="Asia/Shanghai"),
        id="report-supplement-0005",
        name="Daily report midnight supplement",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("[Scheduler] APScheduler initialized: 17:00 daily + 00:05 supplement (Asia/Shanghai)")


def get_next_scheduled() -> str:
    """Return next scheduled generation time for frontend."""
    return _next_scheduled_cst()

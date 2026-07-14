"""日报/周报 Repository。"""

from datetime import date

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.models.daily_report import DailyReport, WeeklyReport, ReportSetting
from .base import BaseRepo


class DailyReportRepo(BaseRepo[DailyReport]):
    model = DailyReport

    def by_date(self, report_date: date) -> DailyReport | None:
        """按日期查询日报。"""
        return self.db.scalar(
            select(DailyReport).where(DailyReport.report_date == report_date)
        )

    def upsert(self, report_date: date, **kwargs) -> DailyReport:
        """按日期 upsert 日报。存在则更新 + 递增 regenerated_count，不存在则创建。"""
        existing = self.by_date(report_date)
        if existing:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(existing, key, value)
            existing.regenerated_count += 1
            existing.generated_at = kwargs.get("generated_at", func.now())
            self.db.flush()
            return existing
        else:
            kwargs["report_date"] = report_date
            kwargs.setdefault("regenerated_count", 0)
            return self.create(**kwargs)


class WeeklyReportRepo(BaseRepo[WeeklyReport]):
    model = WeeklyReport

    def by_week_start(self, week_start: date) -> WeeklyReport | None:
        """按周一日期查询周报。"""
        return self.db.scalar(
            select(WeeklyReport).where(WeeklyReport.week_start == week_start)
        )


class ReportSettingRepo:
    """报告配置 key-value Repository（非 BaseRepo 模式）。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, key: str) -> str | None:
        row = self.db.scalar(
            select(ReportSetting).where(ReportSetting.key == key)
        )
        return row.value if row else None

    def set(self, key: str, value: str) -> None:
        existing = self.db.scalar(
            select(ReportSetting).where(ReportSetting.key == key)
        )
        if existing:
            existing.value = value
        else:
            self.db.add(ReportSetting(key=key, value=value))
        self.db.flush()

    def get_api_key(self) -> str | None:
        return self.get("deepseek_api_key")

    def get_model(self) -> str | None:
        return self.get("deepseek_model")

    def set_api_key(self, api_key: str, model: str | None = None) -> None:
        self.set("deepseek_api_key", api_key)
        if model:
            self.set("deepseek_model", model)

"""日报与周报持久化模型。"""

from datetime import date, datetime

from sqlalchemy import Date, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import Base


class DailyReport(Base):
    """日报持久化 —— 按日期 upsert，统计层必填，洞察层可选。"""

    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    stats_json: Mapped[str] = mapped_column(Text, nullable=False)
    insights_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    regenerated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DailyReport {self.report_date} n={self.regenerated_count}>"


class WeeklyReport(Base):
    """周报快照持久化 —— 每周一凌晨自动生成。"""

    __tablename__ = "weekly_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    stats_json: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<WeeklyReport {self.week_start}>"


class ReportSetting(Base):
    """报告系统配置（API Key 用户覆盖值等），key-value 存储。"""

    __tablename__ = "report_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ReportSetting {self.key}>"

"""日志条目模型 —— 统一分类日志表。"""

from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import Base


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    log_type: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    view_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitor_views.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("situation_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(String(256), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<LogEntry {self.id} type={self.log_type}>"

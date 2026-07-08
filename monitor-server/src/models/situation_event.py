"""事件模型 —— 记录在特定监控视图中发生的异常事件。"""

from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import Base


class SituationEvent(Base):
    __tablename__ = "situation_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    view_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_views.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    exception_id: Mapped[int] = mapped_column(
        ForeignKey("exceptions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 关联
    monitor_view: Mapped["MonitorView"] = relationship("MonitorView")
    exception: Mapped["ExceptionDef"] = relationship("ExceptionDef")

    def __repr__(self) -> str:
        return f"<SituationEvent {self.id} view={self.view_id} at {self.timestamp}>"

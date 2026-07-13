"""逐级上报日志模型 —— 记录每次告警升级的完整链路。"""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import Base


class EscalationLog(Base):
    __tablename__ = "escalation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("situation_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    from_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<EscalationLog alert={self.alert_id} level={self.level} {self.from_role}→{self.to_role}>"

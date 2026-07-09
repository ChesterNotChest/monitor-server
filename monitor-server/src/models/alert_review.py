"""告警审查记录模型 —— 独立于 SituationEvent，记录告警处理动作。"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import Base


class AlertReview(Base):
    __tablename__ = "alert_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("situation_events.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # "handled" | "false_alarm"
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AlertReview {self.id} alert={self.alert_id} action={self.action}>"

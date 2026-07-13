"""响应动作枚举模型 + 告警分组-响应的多对多关联表。"""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Table, Column, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import Base


# ── 多对多关联表 ──────────────────────────────

alert_group_responses = Table(
    "alert_group_responses",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("alert_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("response_id", Integer, ForeignKey("response_actions.id", ondelete="CASCADE"), primary_key=True),
)


# ── ResponseAction 模型 ───────────────────────

class ResponseAction(Base):
    """响应动作 —— 如触发录制、发送通知、激活警报等。"""

    __tablename__ = "response_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 关联
    alert_groups: Mapped[list["AlertGroup"]] = relationship(
        "AlertGroup", secondary=alert_group_responses, back_populates="responses"
    )

    def __repr__(self) -> str:
        return f"<ResponseAction {self.name}>"

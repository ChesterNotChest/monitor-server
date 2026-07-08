"""告警级别分组模型。"""

from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import Base


class AlertGroup(Base):
    __tablename__ = "alert_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 关联
    responses: Mapped[list["ResponseAction"]] = relationship(
        "ResponseAction", secondary="alert_group_responses", back_populates="alert_groups"
    )

    def __repr__(self) -> str:
        return f"<AlertGroup {self.name}>"

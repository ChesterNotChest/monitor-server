"""电子围栏模型——存储围栏定义及其判定参数。

coords 为 4 点不规则四边形（像素坐标系，与 YOLO bbox 同空间）。
"""

from datetime import datetime

from sqlalchemy import ForeignKey, JSON, String, Integer, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import Base


class ElectronicFence(Base):
    __tablename__ = "electronic_fences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    view_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_views.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    coords: Mapped[list] = mapped_column(JSON, nullable=False)
    dwell_time: Mapped[int] = mapped_column(Integer, default=10)
    density: Mapped[float] = mapped_column(Float, default=0.6)
    leave_frames: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # 关联
    monitor_view: Mapped["MonitorView"] = relationship("MonitorView")

    def __repr__(self) -> str:
        return f"<ElectronicFence {self.name} view={self.view_id}>"

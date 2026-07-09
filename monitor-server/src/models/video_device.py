"""视频采集设备模型。"""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import Base


class VideoDevice(Base):
    __tablename__ = "video_devices"
    __table_args__ = (
        UniqueConstraint("node_id", "name", name="uq_video_devices_node_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    streaming: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 关联
    node: Mapped["Node"] = relationship("Node")

    def __repr__(self) -> str:
        return f"<VideoDevice {self.name}>"

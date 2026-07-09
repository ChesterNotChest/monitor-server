"""监控视图模型 —— 组合视频与音频设备。"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import Base


class MonitorView(Base):
    __tablename__ = "monitor_views"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("video_devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    audio_id: Mapped[int] = mapped_column(
        ForeignKey("audio_devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cache_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 关联
    video_device: Mapped["VideoDevice"] = relationship("VideoDevice")
    audio_device: Mapped["AudioDevice"] = relationship("AudioDevice")

    def __repr__(self) -> str:
        return f"<MonitorView {self.id} (video={self.video_id}, audio={self.audio_id})>"

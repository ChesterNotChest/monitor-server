"""监控视图 Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.monitor_view import MonitorView


class MonitorViewRepo(BaseRepo[MonitorView]):
    """监控视图数据访问层。"""

    model = MonitorView

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def device_in_use(self, *, video_id: int | None = None, audio_id: int | None = None) -> bool:
        """检查指定视频或音频设备是否已被任何 View 引用。

        至少需要提供 video_id 或 audio_id 之一。
        """
        query = self.db.query(MonitorView)
        if video_id is not None:
            query = query.filter(MonitorView.video_id == video_id)
        if audio_id is not None:
            query = query.filter(MonitorView.audio_id == audio_id)
        return query.first() is not None

    def find_by_device(self, *, video_id: int | None = None, audio_id: int | None = None) -> list[MonitorView]:
        """查询使用指定设备的所有 View。

        至少需要提供 video_id 或 audio_id 之一。
        """
        query = self.db.query(MonitorView)
        if video_id is not None:
            query = query.filter(MonitorView.video_id == video_id)
        if audio_id is not None:
            query = query.filter(MonitorView.audio_id == audio_id)
        return query.all()

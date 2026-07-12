"""监控视图 Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.monitor_view import MonitorView


class MonitorViewRepo(BaseRepo[MonitorView]):
    """监控视图数据访问层。"""

    model = MonitorView

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(self, **kwargs: object):
        import traceback, logging
        _logger = logging.getLogger(__name__)
        _logger.info("[VIEW-CREATE] video_id=%s audio_id=%s caller=%s",
                    kwargs.get("video_id"), kwargs.get("audio_id"),
                    " <- ".join(f'{f.filename.split(chr(92))[-1]}:{f.lineno}'
                               for f in traceback.extract_stack()[-5:-1]))
        return super().create(**kwargs)

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

    def count_by_video_id(self, video_id: int) -> int:
        """查询引用指定视频设备的 View 数量。"""

        return self.db.query(MonitorView).filter(MonitorView.video_id == video_id).count()

    def count_by_audio_id(self, audio_id: int) -> int:
        """查询引用指定音频设备的 View 数量。"""

        return self.db.query(MonitorView).filter(MonitorView.audio_id == audio_id).count()

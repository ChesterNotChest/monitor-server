"""视频采集设备 Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.video_device import VideoDevice


class VideoDeviceRepo(BaseRepo[VideoDevice]):
    """视频采集设备数据访问层。"""

    model = VideoDevice

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def by_node(self, node_id: int) -> list[VideoDevice]:
        """按所属计算机节点查询所有视频设备。"""
        return (
            self.db.query(VideoDevice)
            .filter(VideoDevice.node_id == node_id)
            .all()
        )

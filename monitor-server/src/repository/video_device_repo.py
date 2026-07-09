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

    def upsert(self, node_id: int, name: str) -> VideoDevice:
        """按 (node_id, name) 判重，不存在时插入。"""

        device = (
            self.db.query(VideoDevice)
            .filter(VideoDevice.node_id == node_id, VideoDevice.name == name)
            .first()
        )
        if device is not None:
            return device
        return self.create(node_id=node_id, name=name)

    def update_streaming(self, device_id: int, streaming: bool) -> VideoDevice | None:
        """更新设备推流状态。"""

        device = self.get(device_id)
        if device is None:
            return None
        device.streaming = streaming
        self.db.add(device)
        self.db.flush()
        return device

"""音频采集设备 Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.audio_device import AudioDevice


class AudioDeviceRepo(BaseRepo[AudioDevice]):
    """音频采集设备数据访问层。"""

    model = AudioDevice

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def by_node(self, node_id: int) -> list[AudioDevice]:
        """按所属计算机节点查询所有音频设备。"""
        return (
            self.db.query(AudioDevice)
            .filter(AudioDevice.node_id == node_id)
            .all()
        )

    def upsert(self, node_id: int, name: str) -> AudioDevice:
        """按 (node_id, name) 判重，不存在时插入。"""

        device = (
            self.db.query(AudioDevice)
            .filter(AudioDevice.node_id == node_id, AudioDevice.name == name)
            .first()
        )
        if device is not None:
            return device
        return self.create(node_id=node_id, name=name)

    def update_streaming(self, device_id: int, streaming: bool) -> AudioDevice | None:
        """更新设备推流状态。"""

        device = self.get(device_id)
        if device is None:
            return None
        device.streaming = streaming
        self.db.add(device)
        self.db.flush()
        return device

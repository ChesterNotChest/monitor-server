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

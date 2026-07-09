"""音视频设备数据访问。"""

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import AudioDevice, VideoDevice

DeviceType = Literal["audio", "video"]


def get_videos_by_node(db: Session, node_id: int) -> list[VideoDevice]:
    return list(db.scalars(select(VideoDevice).where(VideoDevice.node_id == node_id)).all())


def get_audios_by_node(db: Session, node_id: int) -> list[AudioDevice]:
    return list(db.scalars(select(AudioDevice).where(AudioDevice.node_id == node_id)).all())


def get_device_by_id(
    db: Session, device_type: DeviceType, device_id: int
) -> VideoDevice | AudioDevice | None:
    model = VideoDevice if device_type == "video" else AudioDevice
    return db.get(model, device_id)


def upsert_device(
    db: Session, device_type: DeviceType, node_id: int, name: str
) -> VideoDevice | AudioDevice:
    model = VideoDevice if device_type == "video" else AudioDevice
    device = db.scalar(select(model).where(model.node_id == node_id, model.name == name))
    if device is None:
        device = model(node_id=node_id, name=name)
        db.add(device)
        db.commit()
        db.refresh(device)
    return device


def update_streaming(
    db: Session, device_type: DeviceType, device_id: int, streaming: bool
) -> VideoDevice | AudioDevice | None:
    device = get_device_by_id(db, device_type, device_id)
    if device is None:
        return None

    device.streaming = streaming
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

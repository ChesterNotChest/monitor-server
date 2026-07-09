"""Manage raw stream lifecycle from View reference counts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.repository.audio_device_repo import AudioDeviceRepo
from src.repository.monitor_view_repo import MonitorViewRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.schema.wss import UpdateStreamRequest


def _send_update_stream_command(
    node_id: int,
    device_type: str,
    device_id: int,
    enable: bool,
) -> bool:
    """Send UPDATE_STREAM to an online Node."""

    import asyncio

    from src.network.wss.node_handler import NodeOfflineError, registry

    request = UpdateStreamRequest(
        device_type=device_type,
        device_id=device_id,
        enable=enable,
    )

    async def _send() -> bool:
        response = await registry.send_command(node_id, request)
        return response.success

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            return asyncio.run(_send())
        except NodeOfflineError:
            return False

    async def _send_background() -> None:
        try:
            await registry.send_command(node_id, request)
        except NodeOfflineError:
            pass

    loop.create_task(_send_background())
    return True


def get_ref_count(db: Session, device_type: str, device_id: int) -> int:
    """Return how many Views reference a raw device stream."""

    if device_type == "video":
        return MonitorViewRepo(db).count_by_video_id(device_id)
    if device_type == "audio":
        return MonitorViewRepo(db).count_by_audio_id(device_id)
    raise ValueError(f"Unknown device_type: {device_type}")


def check_and_start_stream(db: Session, device_type: str, device_id: int) -> bool:
    """Start raw device streaming when this is the first View reference."""

    if get_ref_count(db, device_type, device_id) > 0:
        return False

    if device_type == "video":
        device = VideoDeviceRepo(db).get(device_id)
    else:
        device = AudioDeviceRepo(db).get(device_id)

    if device is None:
        return False

    if not _send_update_stream_command(device.node_id, device_type, device_id, True):
        return False

    if device_type == "video":
        VideoDeviceRepo(db).update_streaming(device_id, True)
    else:
        AudioDeviceRepo(db).update_streaming(device_id, True)

    return True


def check_and_stop_stream(db: Session, device_type: str, device_id: int) -> bool:
    """Stop raw device streaming when no View references remain."""

    if get_ref_count(db, device_type, device_id) > 0:
        return False

    if device_type == "video":
        device = VideoDeviceRepo(db).get(device_id)
    else:
        device = AudioDeviceRepo(db).get(device_id)

    if device is None:
        return False

    if not _send_update_stream_command(device.node_id, device_type, device_id, False):
        return False

    if device_type == "video":
        VideoDeviceRepo(db).update_streaming(device_id, False)
    else:
        AudioDeviceRepo(db).update_streaming(device_id, False)

    return True

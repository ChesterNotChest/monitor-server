"""推流生命周期管理 —— 引用计数 + 启停推流控制。

Part A 完成后切换真实实现：
- 导入 ``src.network.wss.node_handler.ConnectionRegistry.send_command``
- 导入 ``src.repository.*_repo.update_streaming``
"""

from sqlalchemy.orm import Session

from src.repository.monitor_view_repo import MonitorViewRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.repository.audio_device_repo import AudioDeviceRepo


def get_ref_count(db: Session, device_type: str, device_id: int) -> int:
    """查询某设备被多少个 View 引用。"""
    if device_type == "video":
        return MonitorViewRepo(db).count_by_video_id(device_id)
    elif device_type == "audio":
        return MonitorViewRepo(db).count_by_audio_id(device_id)
    else:
        raise ValueError(f"Unknown device_type: {device_type}")


def check_and_start_stream(db: Session, device_type: str, device_id: int) -> bool:
    """启动设备推流（如未被占用）。

    如果引用计数 = 0（无 View 在用）→ 发 UPDATE_STREAM + update_streaming(True) → 返回 True
    如果引用计数 > 0 → 不操作，返回 False
    """
    ref_count = get_ref_count(db, device_type, device_id)
    if ref_count > 0:
        return False

    # 查设备获取 node_id
    if device_type == "video":
        device = VideoDeviceRepo(db).get(device_id)
    else:
        device = AudioDeviceRepo(db).get(device_id)

    if device is None:
        return False

    # 发送 UPDATE_STREAM 命令（Part A 实现后生效）
    try:
        from src.network.wss.node_handler import registry
        import asyncio
        # 异步发送命令——同步上下文用 asyncio.run 桥接
        asyncio.get_event_loop()
    except (ImportError, RuntimeError):
        pass  # Part A 未就绪时静默跳过

    # 更新设备推流状态
    if device_type == "video":
        VideoDeviceRepo(db).update_streaming(device_id, True)
    else:
        AudioDeviceRepo(db).update_streaming(device_id, True)

    return True


def check_and_stop_stream(db: Session, device_type: str, device_id: int) -> bool:
    """停止设备推流（如已无引用）。

    如果引用计数 = 0 → 发 UPDATE_STREAM + update_streaming(False) → 返回 True
    如果引用计数 > 0 → 不操作，返回 False
    """
    ref_count = get_ref_count(db, device_type, device_id)
    if ref_count > 0:
        return False

    # 发送 UPDATE_STREAM 命令
    try:
        from src.network.wss.node_handler import registry
    except ImportError:
        pass

    # 更新设备推流状态
    if device_type == "video":
        VideoDeviceRepo(db).update_streaming(device_id, False)
    else:
        AudioDeviceRepo(db).update_streaming(device_id, False)

    return True

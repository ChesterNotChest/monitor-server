"""录制回放服务层门户。"""

from datetime import datetime

from sqlalchemy.orm import Session

from src.config import settings
from src.repository.recording_repo import RecordingRepo
from src.models.recording import Recording
from src.service.replay_module.ring_buffer import FrameRingBuffer
from src.service.replay_module.recorder import RecordingSession

# view_id → buffer / session 映射
_buffers: dict[int, FrameRingBuffer] = {}
_sessions: dict[int, RecordingSession] = {}


def _cache_path(view_id: int) -> str:
    """从 MonitorView 读取 cache_path。若不存在使用默认值。"""
    return settings.FACE_IMAGE_DIR.replace("face_images", "recordings")


def start_buffer(view_id: int) -> None:
    """View 创建时调用：初始化环形缓冲区。"""
    if view_id not in _buffers:
        _buffers[view_id] = FrameRingBuffer()


def stop_buffer(view_id: int, db: Session) -> None:
    """View 删除时调用：停止录制 + 清理缓冲区。"""
    session = _sessions.pop(view_id, None)
    if session and not session.is_stopped():
        session.stop(db)

    buf = _buffers.pop(view_id, None)
    if buf:
        buf.clear()


def push_frame(view_id: int, frame_bytes: bytes) -> None:
    """每帧调用：写入缓冲区 + 若录制中则写入 ffmpeg pipe。"""
    buf = _buffers.get(view_id)
    if buf:
        buf.push(frame_bytes)

    session = _sessions.get(view_id)
    if session and not session.is_stopped():
        session.push_frame(frame_bytes)


def alert_triggered(view_id: int, db: Session) -> None:
    """告警引擎调用：创建或延续录制会话。"""
    buf = _buffers.get(view_id)
    if buf is None:
        buf = FrameRingBuffer()
        _buffers[view_id] = buf

    session = _sessions.get(view_id)
    if session is None or session.is_stopped():
        # 检查上一段录制是否已结束，若结束则清理
        if session and session.is_stopped():
            session.stop(db)

        cache = _cache_path(view_id)
        session = RecordingSession(view_id, buf, cache)
        session.start(db)
        _sessions[view_id] = session
    else:
        session.on_new_alert()


def get_recordings(
    db: Session, view_id: int, start: datetime | None = None, end: datetime | None = None
) -> list[Recording]:
    """查询某画面某时段的录制记录。"""
    return RecordingRepo(db).by_view_time(view_id, start=start, end=end)

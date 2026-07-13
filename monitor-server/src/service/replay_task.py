"""录制回放服务层门户。"""

from datetime import datetime

from sqlalchemy.orm import Session

from src.config import settings
from src.repository.recording_repo import RecordingRepo
from src.models.recording import Recording
from src.service.replay_module.ring_buffer import FrameRingBuffer
from src.service.replay_module.recorder import RecordingSession

_buffers: dict[int, FrameRingBuffer] = {}
_sessions: dict[int, RecordingSession] = {}


def _cache_path(view_id: int) -> str:
    return settings.FACE_IMAGE_DIR.replace("face_images", "recordings")


def start_buffer(view_id: int) -> None:
    if view_id not in _buffers:
        _buffers[view_id] = FrameRingBuffer()


def stop_buffer(view_id: int, db: Session) -> None:
    session = _sessions.pop(view_id, None)
    if session and not session.is_stopped():
        session.stop(db)
    buf = _buffers.pop(view_id, None)
    if buf:
        buf.clear()


def push_frame(view_id: int, frame_bytes: bytes) -> None:
    buf = _buffers.get(view_id)
    if buf:
        buf.push(frame_bytes)
    session = _sessions.get(view_id)
    if session and not session.is_stopped():
        session.push_frame(frame_bytes)


def alert_triggered(view_id: int, db: Session, *,
                    action: str = "keep_alive",
                    max_recording_seconds: int = 120,
                    wind_down_seconds: int = 30,
                    alert_details: dict | None = None) -> None:
    """告警引擎调用：管理录制生命周期。

    - action="start": 开始新录制，存储告警详情（录制完成后创建SituationEvent）
    - action="keep_alive": 告警持续，重置倒计时
    - action="end": 告警结束，开始30s缓冲倒计时
    """
    buf = _buffers.get(view_id)
    if buf is None:
        buf = FrameRingBuffer()
        _buffers[view_id] = buf

    session = _sessions.get(view_id)

    if action == "start":
        if session and not session.is_stopped():
            session.stop(db)
        cache = _cache_path(view_id)
        session = RecordingSession(view_id, buf, cache, max_duration=max_recording_seconds, wind_down=wind_down_seconds)
        if alert_details:
            session._alert_details = alert_details
        rec_id = session.start(db)
        _sessions[view_id] = session
        return rec_id
    elif action == "keep_alive" and session and not session.is_stopped():
        session.on_new_alert()
        return session.recording_id
    elif action == "end" and session and not session.is_stopped():
        session.on_alert_end()
        return session.recording_id
    return None


def get_recordings(
    db: Session, view_id: int, start: datetime | None = None, end: datetime | None = None
) -> list[Recording]:
    return RecordingRepo(db).by_view_time(view_id, start=start, end=end)

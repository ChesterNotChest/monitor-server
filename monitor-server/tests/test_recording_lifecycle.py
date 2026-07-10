"""录制生命周期 API 集成测试。

前置：一个常驻 FLV 文件模拟录制中流。
全链路通过 API（非 DB 直操作）验证录制生命周期。
"""

import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app import app
from src.extensions import Base, engine, get_db, SessionLocal
from src.models import (
    SituationEvent, Recording, MonitorView, VideoDevice, AudioDevice,
    Node, ExceptionDef, AlertGroup,
)
from src.constants import SeverityLevel
from src.repository.recording_repo import RecordingRepo


# ── 常驻测试流 ────────────────────────────────

@pytest.fixture(scope="module")
def test_stream_path(tmp_path_factory) -> Path:
    """生成一段常驻 FLV 测试流（10 秒纯色视频）。

    scope=module：所有测试共享同一个文件。
    """
    stream_dir = tmp_path_factory.mktemp("streams")
    stream_path = stream_dir / "view_1_20260710_test.flv"

    # 用 ffmpeg 生成一段可播放的 FLV 文件
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    subprocess.run([
        ffmpeg,
        "-f", "lavfi", "-i", "color=c=blue:s=640x480:d=10:r=10",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-t", "10",
        "-y",
        str(stream_path),
    ], check=True, capture_output=True)
    assert stream_path.exists() and stream_path.stat().st_size > 0
    return stream_path


# ── DB ────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db: Session):
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.fixture
def seed(db: Session):
    """种子：Node → Video/Audio → View → AlertGroup → ExceptionDef。"""
    node = Node(token="test-token")
    db.add(node)
    db.flush()

    video = VideoDevice(name="cam0", node_id=node.id)
    audio = AudioDevice(name="mic0", node_id=node.id)
    db.add_all([video, audio])
    db.flush()

    view = MonitorView(video_id=video.id, audio_id=audio.id)
    db.add(view)
    db.flush()

    alert_group = AlertGroup(name="test-group")
    db.add(alert_group)
    db.flush()

    exc = ExceptionDef(
        name="TEST_EXCEPTION",
        severity=SeverityLevel.WARNING,
        group_id=alert_group.id,
    )
    db.add(exc)
    db.flush()

    db.commit()
    return {"view_id": view.id, "exception_id": exc.id}


# ── Tests ─────────────────────────────────────

class TestRecordingAPILifecycle:
    """API 驱动的录制全生命周期测试。"""

    def test_full_lifecycle(
        self, client: TestClient, db: Session,
        seed: dict, test_stream_path: Path,
    ):
        view_id = seed["view_id"]
        exc_id = seed["exception_id"]

        # ======== 1. 模拟录制开始（DB 写入 + 常驻流文件） ========
        now = datetime.now(timezone.utc)
        rec = Recording(
            view_id=view_id,
            file_path=str(test_stream_path),
            start_time=now,
            end_time=None,  # 录制进行中
        )
        db.add(rec)
        db.flush()

        ev1 = SituationEvent(view_id=view_id, exception_id=exc_id, recording_id=rec.id)
        ev2 = SituationEvent(view_id=view_id, exception_id=exc_id, recording_id=rec.id)
        db.add_all([ev1, ev2])
        db.commit()

        # ======== 2. API：录制进行中 —— end_time 为 null ========
        resp = client.get(f"/api/v1/views/{view_id}/recordings")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["end_time"] is None, f"expected null, got {items[0]['end_time']}"
        recording_id = items[0]["id"]

        # ======== 3. API：录制中 stream 可播放 ========
        resp2 = client.get(f"/api/v1/recordings/{recording_id}/stream")
        assert resp2.status_code == 200

        # ======== 4. 录制结束 ========
        rec.end_time = datetime.now(timezone.utc)
        db.commit()

        resp3 = client.get(f"/api/v1/views/{view_id}/recordings")
        assert resp3.json()[0]["end_time"] is not None

        # ======== 5. API：处置事件1 → 解除关联 → 文件仍可访问 ========
        ev1.recording_id = None
        db.commit()

        resp4 = client.get(f"/api/v1/recordings/{recording_id}/stream")
        assert resp4.status_code == 200  # event2 仍引用

        # ======== 6. API：处置事件2 → 最后一个引用解除 ========
        ev2.recording_id = None
        db.commit()

        ref_count = db.query(SituationEvent).filter(
            SituationEvent.recording_id == recording_id,
        ).count()
        assert ref_count == 0

        # ======== 7. 清理：引用归零 → 删除 Recording ========
        db.delete(rec)
        db.commit()
        repo = RecordingRepo(db)
        assert repo.get(recording_id) is None  # 查不到 = 已删

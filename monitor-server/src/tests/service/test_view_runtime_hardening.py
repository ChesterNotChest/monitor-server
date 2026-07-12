"""Runtime hardening tests for View persistence and merge readiness."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.extensions import Base, get_db
from src.models import AudioDevice, Node, VideoDevice
from src.service import view_task


def _build_client_with_seeded_devices():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    node = Node(token="test-token")
    db.add(node)
    db.flush()
    video = VideoDevice(name="Integrated Camera", node_id=node.id)
    audio = AudioDevice(name="Microphone Array", node_id=node.id)
    db.add_all([video, audio])
    db.commit()
    ids = {"video_id": video.id, "audio_id": audio.id}
    db.close()

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), engine, ids


def test_create_view_commits_view_and_streaming_state(monkeypatch):
    from src.service.view_module import ffmpeg_manager, lifecycle

    monkeypatch.setattr(lifecycle, "_send_update_stream_command", lambda *args: True)
    monkeypatch.setattr(ffmpeg_manager, "start_merge", lambda *args, **kwargs: (True, []))

    client, engine, ids = _build_client_with_seeded_devices()
    try:
        response = client.post(
            "/api/v1/views/",
            json={"audio_id": ids["audio_id"], "video_id": ids["video_id"]},
        )
        assert response.status_code == 200
        view_id = response.json()["id"]

        listed = client.get("/api/v1/views/").json()["views"]
        assert [view["id"] for view in listed] == [view_id]

        videos = client.get("/api/v1/nodes/1/videos").json()["videos"]
        audios = client.get("/api/v1/nodes/1/audios").json()["audios"]
        assert videos[0]["streaming"] is True
        assert audios[0]["streaming"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_create_view_succeeds_without_raw_merge(db, monkeypatch):
    """View 创建不再依赖 raw merge——AI 管线替代了它。"""
    from src.service.view_module import ffmpeg_manager, lifecycle

    node = Node(token="test-token")
    db.add(node)
    db.flush()
    video = VideoDevice(name="Integrated Camera", node_id=node.id)
    audio = AudioDevice(name="Microphone Array", node_id=node.id)
    db.add_all([video, audio])
    db.flush()

    # 记录 start_merge 是否被调用
    merge_called = []
    monkeypatch.setattr(lifecycle, "_send_update_stream_command", lambda *args: True)
    monkeypatch.setattr(
        ffmpeg_manager,
        "start_merge",
        lambda *args, **kwargs: merge_called.append(True) or (True, []),
    )

    result = view_task.create_view(db, audio_id=audio.id, video_id=video.id)

    assert result is not None
    assert result.id is not None
    # 原始合流已禁用——AI 管线取代了它
    assert not merge_called, "start_merge should NOT be called (raw merge disabled)"


def test_wait_for_streams_uses_configured_probe_timeout(monkeypatch):
    from src.network.rtmp import puller

    calls = []

    def fake_is_stream_available(url, timeout=2.0):
        calls.append((url, timeout))
        return True

    monkeypatch.setattr(puller, "is_stream_available", fake_is_stream_available)
    monkeypatch.setattr(puller.settings, "STREAM_PROBE_TIMEOUT", 8.0)

    ready, unavailable = puller.wait_for_streams(["rtmp://raw/video"], timeout=30.0)

    assert ready is True
    assert unavailable == []
    assert calls == [("rtmp://raw/video", 8.0)]


def test_wait_for_streams_caps_probe_to_remaining_total_timeout(monkeypatch):
    from src.network.rtmp import puller

    calls = []

    def fake_is_stream_available(url, timeout=2.0):
        calls.append((url, timeout))
        return True

    monkeypatch.setattr(puller, "is_stream_available", fake_is_stream_available)
    monkeypatch.setattr(puller.settings, "STREAM_PROBE_TIMEOUT", 8.0)

    ready, unavailable = puller.wait_for_streams(["rtmp://raw/video"], timeout=3.0)

    assert ready is True
    assert unavailable == []
    assert len(calls) == 1
    assert calls[0][0] == "rtmp://raw/video"
    assert 0 < calls[0][1] <= 3.0

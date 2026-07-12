"""FFmpeg merge command construction tests."""

from src.service.view_module.ffmpeg_manager import _get_ffmpeg_cmd


def test_get_ffmpeg_cmd_uses_device_names_for_pull_urls(monkeypatch):
    monkeypatch.setenv("RTMP_HOST", "127.0.0.1")
    monkeypatch.setenv("RTMP_PORT", "1935")
    monkeypatch.setenv("SRS_HOST", "127.0.0.1")
    monkeypatch.setenv("SRS_RTMP_PORT", "1936")
    monkeypatch.setenv("DEBUG_WEB_STREAM", "false")

    cmd = _get_ffmpeg_cmd(
        view_id=3,
        video_id=1,
        audio_id=2,
        video_name="Integrated Camera",
        audio_name="Microphone Array",
    )

    assert "rtmp://127.0.0.1:1935/live/Integrated_Camera_video_1" in cmd
    assert "rtmp://127.0.0.1:1935/live/Microphone_Array_audio_2" in cmd
    assert cmd[-1].endswith("/view/3")


def test_play_urls_use_public_srs_endpoint(monkeypatch):
    from src.network.rtmp import pusher

    monkeypatch.setattr(pusher.settings, "SRS_HOST", "stream-server")
    monkeypatch.setattr(pusher.settings, "SRS_RTMP_PORT", 1935)
    monkeypatch.setattr(pusher.settings, "SRS_HTTP_PORT", 8080)
    monkeypatch.setattr(pusher.settings, "SRS_PUBLIC_HOST", "10.126.59.25")
    monkeypatch.setattr(pusher.settings, "SRS_PUBLIC_RTMP_PORT", 1935)
    monkeypatch.setattr(pusher.settings, "SRS_PUBLIC_HTTP_PORT", 8082)
    monkeypatch.setattr(pusher.settings, "DEBUG_WEB_STREAM", False)

    urls = pusher.build_play_urls(7)

    assert urls["rtmp_url"] == "rtmp://10.126.59.25:1935/view/7"
    assert urls["flv_url"] == "http://10.126.59.25:8082/view/7.flv"
    assert urls["webrtc_url"] == "http://10.126.59.25:1985/rtc/v1/whep/?app=view&stream=7"

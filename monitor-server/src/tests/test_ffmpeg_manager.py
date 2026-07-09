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

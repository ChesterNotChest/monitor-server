"""RecordingSession 冒烟测试。

注: RecordingSession 已切为 RTMP pull 架构 (yuyu branch)。
旧 frame-pipe API (width/height/fps) 已移除。
"""

from src.service.replay_module.ring_buffer import FrameRingBuffer


class TestRecordingSession:
    def test_constructor_defaults(self):
        """新 API: RecordingSession(view_id, buffer, cache_path, max_duration, wind_down)。"""
        from src.service.replay_module.recorder import RecordingSession
        buf = FrameRingBuffer(max_seconds=1, fps=10)
        session = RecordingSession(view_id=1, buffer=buf, cache_path="/tmp")
        assert session.max_duration == 10
        assert session.wind_down == 10
        assert session.is_stopped() is False

    def test_constructor_custom_params(self):
        """max_duration 和 wind_down 可自定义。"""
        from src.service.replay_module.recorder import RecordingSession
        buf = FrameRingBuffer(max_seconds=1, fps=10)
        session = RecordingSession(view_id=2, buffer=buf, cache_path="/tmp",
                                   max_duration=30, wind_down=15)
        assert session.max_duration == 30
        assert session.wind_down == 15

    def test_on_new_alert_and_on_alert_end(self):
        """on_new_alert 清除 wind_down; on_alert_end 开始 wind_down 倒计时。"""
        from src.service.replay_module.recorder import RecordingSession
        buf = FrameRingBuffer(max_seconds=1, fps=10)
        session = RecordingSession(view_id=3, buffer=buf, cache_path="/tmp")
        session._alert_ended = True
        session.on_new_alert()
        assert session._alert_ended is False

        session.on_alert_end()
        assert session._alert_ended is True
        assert session._wind_down_start > 0

    def test_push_frame_is_noop(self):
        """push_frame 现在是 no-op（从 SRS RTMP 拉流，不从 pipe 喂帧）。"""
        from src.service.replay_module.recorder import RecordingSession
        buf = FrameRingBuffer(max_seconds=1, fps=10)
        session = RecordingSession(view_id=4, buffer=buf, cache_path="/tmp")
        # 不应抛异常
        session.push_frame(b"anything")

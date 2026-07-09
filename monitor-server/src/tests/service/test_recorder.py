"""RecordingSession 冒烟测试。"""

import os
import tempfile
import time
import threading

from src.service.replay_module.ring_buffer import FrameRingBuffer
from src.service.replay_module.recorder import RecordingSession


class TestRecordingSession:
    def test_start_and_stop(self, db):
        buf = FrameRingBuffer(max_seconds=1, fps=10)
        for i in range(5):
            buf.push(b"x" * 100)  # tiny fake frames

        with tempfile.TemporaryDirectory() as tmpdir:
            session = RecordingSession(view_id=1, buffer=buf, cache_path=tmpdir, width=32, height=32, fps=10)
            session.start(db)
            # Let it record a bit
            time.sleep(1)
            session.push_frame(b"y" * 100)
            path = session.stop(db)

            if path:
                assert os.path.exists(path)

    def test_on_new_alert_resets_timer(self):
        buf = FrameRingBuffer(max_seconds=1, fps=10)
        session = RecordingSession(view_id=2, buffer=buf, cache_path="/tmp", width=32, height=32, fps=10)
        session._silence_seconds = 50
        session.on_new_alert()
        assert session._silence_seconds == 0

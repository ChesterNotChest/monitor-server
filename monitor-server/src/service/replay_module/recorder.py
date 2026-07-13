"""录制会话 —— 从 SRS 拉取 RTMP 流录制到本地 FLV 文件。"""

import logging
import os
import subprocess
import threading
import time as _time
from datetime import datetime, timezone
from pathlib import Path

from src.config import settings
from src.service.replay_module.ring_buffer import FrameRingBuffer

logger = logging.getLogger(__name__)


class RecordingSession:
    def __init__(self, view_id: int, buffer: FrameRingBuffer, cache_path: str,
                 max_duration: int = 10, wind_down: int = 10):
        self.view_id = view_id
        self.cache_path = cache_path
        self.max_duration = max_duration
        self.wind_down = wind_down

        self._start_mono: float = 0
        self._alert_ended = False
        self._wind_down_start: float = 0
        self._stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        self._ffmpeg_proc: subprocess.Popen | None = None
        self.start_time: datetime | None = None
        self.output_path: str | None = None
        self.recording_id: int | None = None

    def start(self, db) -> int | None:
        """从 SRS 拉取 view/{id} RTMP 流，录制到本地 FLV。返回 recording_id。"""
        from src.repository.recording_repo import RecordingRepo
        now = datetime.now(timezone.utc)
        self.start_time = now
        self._start_mono = _time.monotonic()

        cache_dir = Path(self.cache_path)
        cache_dir.mkdir(parents=True, exist_ok=True)
        ts = now.strftime("%Y%m%d_%H%M%S")
        filename = f"view_{self.view_id}_{ts}.flv"
        self.output_path = str(cache_dir / filename)

        # 从 SRS 拉流，stream copy（不需重新编码，FLV 格式干净）
        rtmp_url = f"rtmp://{settings.SRS_HOST}:{settings.SRS_RTMP_PORT}/view/{self.view_id}"
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", rtmp_url,
            "-c:v", "copy", "-an",
            "-f", "flv", self.output_path,
        ]

        self._ffmpeg_proc = subprocess.Popen(ffmpeg_cmd,
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        recording = RecordingRepo(db).create(
            view_id=self.view_id, file_path=self.output_path,
            start_time=self.start_time, end_time=None,
        )
        db.commit()
        self.recording_id = recording.id

        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self._monitor_thread.start()
        logger.info(
            "[Replay] START view=%d rec=%d max_dur=%ds wind_down=%ds",
            self.view_id, self.recording_id, self.max_duration, self.wind_down,
        )
        return self.recording_id

    def _monitor(self):
        while not self._stop_event.wait(timeout=1.0):
            elapsed = _time.monotonic() - self._start_mono
            if elapsed >= self.max_duration:
                logger.info(
                    "[Replay] MAX_DUR stop view=%d rec=%d elapsed=%.0fs",
                    self.view_id, self.recording_id, elapsed,
                )
                self._stop_ffmpeg()
                break
            if self._alert_ended:
                wind_elapsed = _time.monotonic() - self._wind_down_start
                if wind_elapsed >= self.wind_down:
                    logger.info(
                        "[Replay] WIND_DOWN stop view=%d rec=%d total=%.0fs",
                        self.view_id, self.recording_id, elapsed,
                    )
                    self._stop_ffmpeg()
                    break

    def _stop_ffmpeg(self):
        """终止 ffmpeg 进程并设停止标志"""
        self._stop_event.set()
        if self._ffmpeg_proc:
            try: self._ffmpeg_proc.terminate()
            except Exception: pass
            try:
                self._ffmpeg_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try: self._ffmpeg_proc.kill()
                except Exception: pass

    def on_new_alert(self):
        self._alert_ended = False
        logger.info(
            "[Replay] KEEP_ALIVE view=%d rec=%d",
            self.view_id, self.recording_id,
        )

    def on_alert_end(self):
        self._alert_ended = True
        self._wind_down_start = _time.monotonic()
        logger.info(
            "[Replay] WIND_DOWN view=%d rec=%d wait=%ds",
            self.view_id, self.recording_id, self.wind_down,
        )

    def is_stopped(self) -> bool: return self._stop_event.is_set()

    def push_frame(self, frame_bytes: bytes) -> None:
        pass  # 不需要 pipe——直接从 SRS 拉流

    def stop(self, db) -> int | None:
        self._stop_event.set()
        if self._ffmpeg_proc:
            try: self._ffmpeg_proc.terminate()
            except Exception: pass
            try: self._ffmpeg_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ffmpeg_proc.kill(); self._ffmpeg_proc.wait()

        if self.recording_id:
            from src.repository.recording_repo import RecordingRepo
            rec = RecordingRepo(db).get(self.recording_id)
            if rec:
                rec.end_time = datetime.now(timezone.utc)
                db.commit()
        return self.recording_id

"""录制引擎 —— 持续录制会话管理。"""

import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from src.config import settings
from src.repository.recording_repo import RecordingRepo
from src.service.replay_module.ring_buffer import FrameRingBuffer


class RecordingSession:
    """一次持续录制会话。

    告警触发时创建，持续写帧到 ffmpeg pipe。
    每次新告警调用 on_new_alert() 重置静默计时器。
    连续 ``RECORD_STOP_SILENCE_SECONDS`` 秒无新告警则停止。
    """

    def __init__(
        self, view_id: int, buffer: FrameRingBuffer, cache_path: str,
        width: int = 1920, height: int = 1080, fps: int = 25,
    ):
        self.view_id = view_id
        self.buffer = buffer
        self.cache_path = cache_path
        self.width = width
        self.height = height
        self.fps = fps
        self.format = getattr(buffer, "format", "raw_bgr24")

        self._silence_seconds = 0
        self._stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        self._ffmpeg_proc: subprocess.Popen | None = None
        self.start_time: datetime | None = None
        self.output_path: str | None = None

    def start(self, db) -> str:
        """开始录制：dump 历史帧 + 启动 ffmpeg pipe + 监听线程。"""
        now = datetime.now(timezone.utc)
        self.start_time = now

        cache_dir = Path(self.cache_path)
        cache_dir.mkdir(parents=True, exist_ok=True)
        ts = now.strftime("%Y%m%d_%H%M%S")
        filename = f"view_{self.view_id}_{ts}.flv"
        self.output_path = str(cache_dir / filename)

        # 启动 ffmpeg pipe —— 按帧格式切换参数
        if self.format == "jpeg":
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "image2pipe", "-c:v", "mjpeg",
                "-use_wallclock_as_timestamps", "1",
                "-i", "pipe:0",
                "-c:v", "copy", "-f", "flv",
                self.output_path,
            ]
        else:
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "rawvideo", "-pix_fmt", "bgr24",
                "-s", f"{self.width}x{self.height}", "-r", str(self.fps),
                "-i", "pipe:0",
                "-c:v", "libx264", "-f", "flv",
                self.output_path,
            ]

        self._ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 写入历史帧
        history = self.buffer.dump_all()
        for frame in history:
            try:
                self._ffmpeg_proc.stdin.write(frame)
            except (BrokenPipeError, OSError):
                break

        # 启动静默监控线程
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        return filename

    def push_frame(self, frame_bytes: bytes) -> None:
        """写入一帧到 ffmpeg pipe。"""
        if self._ffmpeg_proc and self._ffmpeg_proc.stdin:
            try:
                self._ffmpeg_proc.stdin.write(frame_bytes)
            except (BrokenPipeError, OSError):
                pass

    def on_new_alert(self) -> None:
        """新告警触发，重置静默计时器。"""
        self._silence_seconds = 0

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def _monitor_loop(self) -> None:
        """后台线程：每秒检查静默计时器。"""
        check_interval = settings.RECORD_STOP_SILENCE_SECONDS
        while self._silence_seconds < check_interval:
            if self._stop_event.wait(timeout=1):
                return
            self._silence_seconds += 1
        self._stop_event.set()

    def stop(self, db) -> str | None:
        """停止录制：关闭 ffmpeg，写入 Recording 记录。"""
        if self._stop_event.is_set() is False and self._ffmpeg_proc:
            # 提前停止（如 View 删除）
            self._stop_event.set()

        if self._ffmpeg_proc and self._ffmpeg_proc.stdin:
            try:
                self._ffmpeg_proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            try:
                self._ffmpeg_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ffmpeg_proc.kill()
                self._ffmpeg_proc.wait()

        if self.output_path and os.path.exists(self.output_path):
            end_time = datetime.now(timezone.utc)
            RecordingRepo(db).create(
                view_id=self.view_id,
                file_path=self.output_path,
                start_time=self.start_time,
                end_time=end_time,
            )
            return self.output_path
        return None

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
        self.buffer = buffer
        self.cache_path = cache_path
        self.max_duration = max_duration
        self.wind_down = wind_down

        self._start_mono: float = 0
        self._alert_ended = False
        self._wind_down_start: float = 0
        self._stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        self._ffmpeg_proc: subprocess.Popen | None = None
        self._pre_roll_path: str | None = None
        self.start_time: datetime | None = None
        self.output_path: str | None = None
        self.recording_id: int | None = None

    def start(self, db) -> int | None:
        """从 SRS 拉取 view/{id} RTMP 流，拼 30s 预卷 + 正向录制到 FLV。"""
        from src.repository.recording_repo import RecordingRepo
        now = datetime.now(timezone.utc)
        self.start_time = now

        cache_dir = Path(self.cache_path)
        cache_dir.mkdir(parents=True, exist_ok=True)
        ts = now.strftime("%Y%m%d_%H%M%S")
        self.output_path = str(cache_dir / f"view_{self.view_id}_{ts}.flv")

        # 3路拼合: 预卷(环形缓冲) → 正向录制(SRS RTMP)
        pre_roll = str(cache_dir / f"view_{self.view_id}_{ts}_preroll.flv")
        frames = self.buffer.dump_all()
        if frames and self.buffer.width > 0 and self.buffer.height > 0:
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                    "-s", f"{self.buffer.width}x{self.buffer.height}",
                    "-r", str(max(self.buffer.fps, 1)), "-i", "pipe:0",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-an", "-f", "flv", pre_roll,
                ], input=b"".join(frames), capture_output=True, timeout=15)
                if Path(pre_roll).exists():
                    self._pre_roll_path = pre_roll
                    logger.info("[Replay] Pre-roll encoded: %d frames %dx%d",
                               len(frames), self.buffer.width, self.buffer.height)
                else:
                    logger.warning("[Replay] Pre-roll encoding produced no file")
                    self._pre_roll_path = None
            except Exception as e:
                logger.warning("[Replay] Pre-roll encoding failed: %s", e)
                self._pre_roll_path = None
        else:
            logger.info("[Replay] Pre-roll skipped: frames=%d size=%dx%d",
                       len(frames), self.buffer.width, self.buffer.height)
            self._pre_roll_path = None

        self._start_mono = _time.monotonic()  # 正向录制从此刻计时（不含预卷）
        rtmp_url = f"rtmp://{settings.SRS_HOST}:{settings.SRS_RTMP_PORT}/view/{self.view_id}"
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", rtmp_url,
            "-c:v", "copy", "-an",
            "-f", "flv", self.output_path,
        ]

        self._ffmpeg_proc = subprocess.Popen(ffmpeg_cmd,
                                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self._stderr_reader = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_reader.start()

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

    def _drain_stderr(self) -> None:
        """后台读取 ffmpeg stderr 避免管道缓冲区满。"""
        if self._ffmpeg_proc and self._ffmpeg_proc.stderr:
            try:
                # 读到的内容暂不存，仅排空管道；退出时 _dump_stderr 会再读一次
                while self._ffmpeg_proc.poll() is None:
                    self._ffmpeg_proc.stderr.read1(8192)
            except Exception:
                pass

    def _dump_stderr(self) -> None:
        """从 stderr 管道读取最后一截内容用于诊断。"""
        if self._ffmpeg_proc and self._ffmpeg_proc.stderr:
            try:
                # 先排空 read1 缓冲区，再 read 剩余
                while True:
                    chunk = self._ffmpeg_proc.stderr.read1(8192)
                    if not chunk:
                        break
                remaining = self._ffmpeg_proc.stderr.read()
                if remaining:
                    lines = remaining.decode("utf-8", errors="replace").strip().splitlines()
                    tail = lines[-1] if lines else remaining.decode("utf-8", errors="replace")[:500]
                    logger.debug("[Replay] ffmpeg stderr tail: %s", tail)
            except Exception:
                pass

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
        """终止 ffmpeg、拼预卷、写 end_time"""
        self._stop_event.set()
        self._dump_stderr()
        if self._ffmpeg_proc:
            try: self._ffmpeg_proc.terminate()
            except Exception: pass
            try:
                self._ffmpeg_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try: self._ffmpeg_proc.kill()
                except Exception: pass

        # 拼合预卷 + 正向录制
        if self._pre_roll_path and self.output_path and Path(self._pre_roll_path).exists():
            import os as _os
            merged = self.output_path + ".merged.flv"
            try:
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", "concat:" + self._pre_roll_path + "|" + self.output_path,
                    "-c", "copy", "-f", "flv", merged,
                ], capture_output=True, timeout=30)
                _os.replace(merged, self.output_path)
                logger.info("[Replay] Pre-roll merged: %s → %s", self._pre_roll_path, self.output_path)
            except Exception as e:
                logger.warning("[Replay] Pre-roll merge failed: %s", e)
            try: _os.remove(self._pre_roll_path)
            except Exception: pass
            self._pre_roll_path = None
        # 回填 end_time（monitor 线程无 db 参数，自己开 session）
        if self.recording_id:
            try:
                from src.extensions import SessionLocal
                from src.repository.recording_repo import RecordingRepo
                _db = SessionLocal()
                try:
                    rec = RecordingRepo(_db).get(self.recording_id)
                    if rec and rec.end_time is None:
                        rec.end_time = datetime.now(timezone.utc)
                        _db.commit()
                finally:
                    _db.close()
            except Exception:
                pass

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

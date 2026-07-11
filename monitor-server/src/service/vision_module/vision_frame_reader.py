"""帧管线——OpenCV 从 SRS 拉取 RTMP 视频流，逐帧解码。

支持断流重连、FPS 控制、三态状态机（IDLE → ACTIVE → ERROR）。
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import contextmanager
from enum import Enum, auto

import cv2
import numpy as np

from src.config import settings
from src.network.rtmp.puller import build_pull_url

logger = logging.getLogger(__name__)

# ── 重连参数 ──────────────────────────────────
_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 60.0
_BACKOFF_MULTIPLIER = 2.0
_MAX_CONSECUTIVE_FAILURES = 10


class FrameReaderState(Enum):
    IDLE = auto()
    ACTIVE = auto()
    ERROR = auto()




class FrameReader:
    """OpenCV RTMP 帧读取器。每个 View 一个独立实例。"""

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._state = FrameReaderState.IDLE
        self._fps_target: int = settings.FPS_TARGET
        self._source_fps: float = 0.0
        self._frame_interval: float = 0.0
        self._consecutive_failures: int = 0
        self._frame_id: int = 0
        self._open_time: float = 0.0

    # ── Properties ──────────────────────────────

    @property
    def state(self) -> FrameReaderState:
        return self._state

    @property
    def fps(self) -> float:
        return self._source_fps

    @property
    def open_time(self) -> float:
        """Reader 打开时的墙上时钟（Unix 秒），用于计算帧采集时刻。"""
        return self._open_time

    # ── Lifecycle ───────────────────────────────

    def open(self, video_id: int, video_name: str) -> bool:
        """建立 RTMP 连接并初始化帧率控制。

        Returns:
            True if connected successfully.
        """
        url = build_pull_url(video_name, "video", video_id)
        logger.info("FrameReader connecting to %s", url)
        import os
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "timeout;5000000")
        self._cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not self._cap.isOpened():
            logger.error("FrameReader failed to open %s", url)
            self._state = FrameReaderState.ERROR
            return False

        self._source_fps = self._cap.get(cv2.CAP_PROP_FPS) or settings.FPS_TARGET
        self._frame_interval = 1.0 / min(self._source_fps, self._fps_target)
        self._state = FrameReaderState.ACTIVE
        self._consecutive_failures = 0
        self._frame_id = 0
        self._open_time = time.time()
        logger.info(
            "FrameReader connected (source_fps=%.1f, target_fps=%d, interval=%.3fs)",
            self._source_fps, self._fps_target, self._frame_interval,
        )
        return True

    def close(self) -> None:
        """释放 VideoCapture 资源。"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._state = FrameReaderState.IDLE

    # ── Frame iteration ──────────────────────────

    def read(self) -> tuple[bool, np.ndarray | None, float, int]:
        """读取一帧。内置 FPS 控制和断流重连。

        Returns:
            (success, frame, timestamp, frame_id)
            — frame 为 BGR24 numpy array；success=False 表示断流且重连失败。
        """
        if self._state == FrameReaderState.ERROR:
            return False, None, 0.0, -1

        ret, frame = self._read_internal()
        if not ret:
            return self._handle_read_failure()

        self._consecutive_failures = 0
        self._frame_id += 1
        timestamp = time.time() - self._open_time
        return True, frame, timestamp, self._frame_id

    def _read_internal(self) -> tuple[bool, np.ndarray | None]:
        """底层读取，直接取最新帧（不做跳帧窗口——RTMP read 本身已阻塞等帧）。"""
        if self._cap is None:
            return False, None
        ret, frame = self._cap.read()
        return ret, frame

    def _handle_read_failure(
        self,
    ) -> tuple[bool, np.ndarray | None, float, int]:
        """断流重连。"""
        self._consecutive_failures += 1
        if self._consecutive_failures > _MAX_CONSECUTIVE_FAILURES:
            self._state = FrameReaderState.ERROR
            logger.error(
                "FrameReader ERROR after %d consecutive failures",
                self._consecutive_failures,
            )
            return False, None, 0.0, -1

        backoff = min(
            _INITIAL_BACKOFF * (_BACKOFF_MULTIPLIER ** (self._consecutive_failures - 1)),
            _MAX_BACKOFF,
        )
        logger.warning(
            "FrameReader read failure (%d/%d), reconnecting in %.1fs ...",
            self._consecutive_failures, _MAX_CONSECUTIVE_FAILURES, backoff,
        )
        time.sleep(backoff)

        # 尝试重连
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._cap is None and hasattr(self, '_last_url'):
            self._cap = cv2.VideoCapture(self._last_url)
        if self._cap is not None and self._cap.isOpened():
            self._state = FrameReaderState.ACTIVE
            return True, None, 0.0, -1  # 重连成功，下一帧正常读

        return False, None, 0.0, -1

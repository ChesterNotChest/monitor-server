"""帧环形缓冲区 —— 缓存最近 N 秒的帧数据。"""

import threading
from collections import deque

from src.config import settings


class FrameRingBuffer:
    """线程安全的帧环形缓冲区。

    每个 MonitorView 一个实例，缓存最近 max_seconds 秒的帧。
    """

    def __init__(self, max_seconds: int | None = None, fps: int = 25):
        max_sec = max_seconds or settings.CACHE_DURATION_SECONDS
        self._frames: deque[bytes] = deque(maxlen=max_sec * fps)
        self._lock = threading.Lock()

    def push(self, frame_bytes: bytes) -> None:
        """写入一帧。超出容量时自动丢弃最旧帧。"""
        with self._lock:
            self._frames.append(frame_bytes)

    def dump_all(self) -> list[bytes]:
        """返回当前缓存的所有帧（快照），不清空。"""
        with self._lock:
            return list(self._frames)

    def clear(self) -> None:
        """清空缓冲区。"""
        with self._lock:
            self._frames.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._frames)

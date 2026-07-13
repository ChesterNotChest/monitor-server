"""内存事件总线——AI 模块间发布/订阅通道。

事件类型常量:
    ENTITY  - YOLO 目标检测结果
    ACTION  - SlowFast 行为识别结果
    SOUND   - YAMNet 音频分类结果
    FACE    - 人脸识别结果
    FENCE   - 电子围栏事件
    RECORDING - 录制控制信号

Usage::

    from src.service.vision_module.event_bus import event_bus

    async def on_entity(payload: dict) -> None:
        print(payload)

    event_bus.subscribe("ENTITY", on_entity)
    await event_bus.publish("ENTITY", {"view_id": 1, "entities": [...]})
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# ── 事件类型常量 ──────────────────────────────
ENTITY = "ENTITY"
ACTION = "ACTION"
SOUND = "SOUND"
FACE = "FACE"
FENCE = "FENCE"
RECORDING = "RECORDING"


class EventBus:
    """内存中的发布/订阅通道。async-safe——使用 asyncio.Lock 保护。"""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(
        self, event_type: str, callback: Callable[[dict], Awaitable[None]],
    ) -> None:
        """注册事件回调。同一 callback 不重复注册。"""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    async def unsubscribe(
        self, event_type: str, callback: Callable[[dict], Awaitable[None]],
    ) -> None:
        """移除事件回调。"""
        async with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                except ValueError:
                    pass

    async def publish(self, event_type: str, payload: dict) -> None:
        """向所有订阅者广播事件。单个订阅者异常不影响其他订阅者。"""
        async with self._lock:
            subscribers = list(self._subscribers.get(event_type, []))
        if subscribers:
            logger.info(
                "[EventBus] publish %s keys=%s subs=%d",
                event_type, list(payload.keys()), len(subscribers),
            )
        # 无订阅者时静默跳过 — 避免每帧上百行噪声
        for callback in subscribers:
            try:
                await callback(payload)
            except Exception:
                logger.exception(
                    "EventBus subscriber %s failed for event %s",
                    getattr(callback, "__name__", callback),
                    event_type,
                )


# ── 全局单例 ──────────────────────────────────
event_bus = EventBus()

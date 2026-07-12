"""Vision Pipeline 门户函数——被 API 层或其他 service 模块调用。

与 view_task.py / alert_task.py 同级，负责 AI 管线的启停编排。
"""

from __future__ import annotations

import asyncio
import logging

from src.service.alert_module.engine import AlertEngine
from src.service.audio_module.audio_yamnet import YamnetRunner
from src.service.vision_module.vision_pipeline import AIPipeline

logger = logging.getLogger(__name__)

# ── 活跃管线注册表 ──
_active_pipelines: dict[int, AIPipeline] = {}
_alert_engines: dict[int, AlertEngine] = {}
_yamnet_runners: dict[int, YamnetRunner] = {}
_pipeline_loops: dict[int, asyncio.AbstractEventLoop] = {}
_pipeline_stop_events: dict[int, asyncio.Event] = {}


async def start_pipeline(view_id: int, video_id: int, video_name: str,
                         audio_id: int | None = None,
                         audio_name: str = "") -> bool:
    """启动指定 View 的 AI 推理管线（视觉 + 告警引擎 + 可选音频分类）。

    Returns:
        True if started successfully.
    """
    if view_id in _active_pipelines:
        logger.warning("Pipeline already running for view_id=%d", view_id)
        return False

    owner_loop = asyncio.get_running_loop()

    # 1. 启动视觉管线 (Part A)
    pipeline = AIPipeline()
    if not await pipeline.start(view_id, video_id, video_name, audio_id, audio_name):
        return False
    _active_pipelines[view_id] = pipeline
    _pipeline_loops[view_id] = owner_loop
    _pipeline_stop_events[view_id] = asyncio.Event()

    # 1.5 注册 Part B 模块 (ByteTrack + Face + Fence + SlowFast)
    try:
        from src.service.vision_module.video_ai_processor import register_video_ai_hooks
        register_video_ai_hooks(pipeline, view_id)
        logger.info("Part B hooks registered for view_id=%d", view_id)
    except Exception:
        logger.warning("Failed to register Part B hooks for view_id=%d", view_id, exc_info=True)

    # 2. 启动告警引擎 (Part C)
    alert = AlertEngine(view_id)
    await alert.start()
    _alert_engines[view_id] = alert
    logger.info("AlertEngine started for view_id=%d", view_id)

    # 3. 有音频设备时启动 YAMNet (Part C)
    if audio_id is not None:
        yamnet = YamnetRunner(view_id, audio_id, audio_name)
        asyncio.create_task(yamnet.run())
        _yamnet_runners[view_id] = yamnet
        logger.info("YamnetRunner started for view_id=%d audio_id=%d", view_id, audio_id)

    return True


async def wait_pipeline_stopped(view_id: int) -> None:
    """Wait until ``stop_pipeline`` releases the owner loop keepalive."""

    event = _pipeline_stop_events.get(view_id)
    if event is not None:
        await event.wait()


async def stop_pipeline(view_id: int) -> None:
    """停止指定 View 的 AI 推理管线（YAMNet → AlertEngine → AIPipeline）。"""

    owner_loop = _pipeline_loops.get(view_id)
    current_loop = asyncio.get_running_loop()
    if owner_loop is not None and owner_loop is not current_loop and owner_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(
            _stop_pipeline_on_owner_loop(view_id),
            owner_loop,
        )
        await asyncio.wrap_future(future)
        return

    await _stop_pipeline_on_owner_loop(view_id)


async def _stop_pipeline_on_owner_loop(view_id: int) -> None:
    # 先停 YAMNet
    yamnet = _yamnet_runners.pop(view_id, None)
    if yamnet:
        await yamnet.stop()
        logger.info("YamnetRunner stopped for view_id=%d", view_id)

    # 再停告警引擎
    alert = _alert_engines.pop(view_id, None)
    if alert:
        await alert.stop()
        logger.info("AlertEngine stopped for view_id=%d", view_id)

    # 最后停视觉管线
    pipeline = _active_pipelines.pop(view_id, None)
    if pipeline:
        await pipeline.stop()

    _pipeline_loops.pop(view_id, None)
    event = _pipeline_stop_events.pop(view_id, None)
    if event is not None and not event.is_set():
        event.set()


async def stop_all() -> None:
    """停止所有活跃管线（Server 关闭时调用）。"""
    for view_id in list(_active_pipelines.keys()):
        await stop_pipeline(view_id)

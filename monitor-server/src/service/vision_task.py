"""Vision Pipeline 门户函数——被 API 层或其他 service 模块调用。

与 view_task.py / alert_task.py 同级，负责 AI 管线的启停编排。
"""

from __future__ import annotations

import asyncio
import logging

from src.service.alert_module.engine import AlertEngine
from src.service.audio_module.audio_yamnet import YamnetRunner
from src.service.vision_module.vision_pipeline import AIPipeline
from src.service.vision_module.vision_event_bus import event_bus, RECORDING
from src.service import replay_task

logger = logging.getLogger(__name__)

# ── 活跃管线注册表 ──
_active_pipelines: dict[int, AIPipeline] = {}
_alert_engines: dict[int, AlertEngine] = {}
_yamnet_runners: dict[int, YamnetRunner] = {}


async def wait_pipeline_ready(view_id: int, timeout: float = 30.0) -> bool:
    """等待 AI pipeline 首帧推流就绪，超时返回 False。"""
    pipeline = _active_pipelines.get(view_id)
    if pipeline is None:
        return False
    try:
        await asyncio.wait_for(pipeline.pipeline_ready.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False
_pipeline_loops: dict[int, asyncio.AbstractEventLoop] = {}
_pipeline_stop_events: dict[int, asyncio.Event] = {}
_recording_subscribed: bool = False


async def _on_recording(payload: dict) -> None:
    """EventBus RECORDING 订阅者：桥接 AlertEngine → replay_task 录制会话。"""
    view_id = payload.get("view_id")
    if view_id is None:
        return
    action = payload.get("action", "keep_alive")
    max_dur = payload.get("max_recording_seconds", 120)
    alert_details = payload.get("alert_details")
    from src.extensions import SessionLocal
    db = SessionLocal()
    try:
        replay_task.alert_triggered(
            view_id, db, action=action,
            max_recording_seconds=payload.get("max_recording_seconds", 120),
            wind_down_seconds=payload.get("wind_down_seconds", 30),
            alert_details=alert_details,
        )
    except Exception:
        logger.exception("Recording subscriber failed for view_id=%d", view_id)
    finally:
        db.close()


async def start_pipeline(view_id: int, video_id: int, video_name: str,
                         audio_id: int | None = None,
                         audio_name: str = "",
                         stream_url: str | None = None) -> bool:
    """启动指定 View 的 AI 推理管线（视觉 + 告警引擎 + 可选音频分类）。

    Returns:
        True if started successfully.
    """
    import traceback as _tb
    logger.info("[Pipeline] START view=%d video=%s(%d) audio=%s(%s) stack=%s",
                view_id, video_name, video_id,
                audio_name or "none", audio_id or "none",
                "".join(_tb.format_stack()[-3]).strip().replace('\n',' ')[:120])
    if view_id in _active_pipelines:
        logger.warning("[Pipeline] SKIP view=%d (already active, count=%d)",
                      view_id, len(_active_pipelines))
        return False

    owner_loop = asyncio.get_running_loop()

    # 1. 启动视觉管线 (Part A)
    pipeline = AIPipeline()
    if not await pipeline.start(view_id, video_id, video_name, audio_id, audio_name, stream_url=stream_url):
        return False
    _active_pipelines[view_id] = pipeline
    _pipeline_loops[view_id] = owner_loop
    _pipeline_stop_events[view_id] = asyncio.Event()

    # 1.5 注册 Part B 模块 (ByteTrack + Face + Fence + SlowFast)
    try:
        from src.extensions import SessionLocal
        from src.service.vision_module.video_ai_processor import register_video_ai_hooks
        db = SessionLocal()
        register_video_ai_hooks(pipeline, view_id, db=db)
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

    # 4. 初始化录制缓冲区 + 注册 RECORDING 订阅者
    replay_task.start_buffer(view_id)
    logger.info("Recording buffer started for view_id=%d", view_id)

    global _recording_subscribed
    if not _recording_subscribed:
        await event_bus.subscribe(RECORDING, _on_recording)
        _recording_subscribed = True
        logger.info("RECORDING subscriber registered")

    return True


async def wait_pipeline_stopped(view_id: int) -> None:
    """Wait until ``stop_pipeline`` releases the owner loop keepalive."""

    event = _pipeline_stop_events.get(view_id)
    if event is not None:
        await event.wait()


async def stop_pipeline(view_id: int) -> None:
    """停止指定 View 的 AI 推理管线（YAMNet → AlertEngine → AIPipeline → 录制清理）。"""

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

    # 清理录制缓冲区
    from src.extensions import SessionLocal
    db = SessionLocal()
    try:
        replay_task.stop_buffer(view_id, db)
        logger.info("Recording buffer stopped for view_id=%d", view_id)
    except Exception:
        logger.exception("Failed to stop recording buffer for view_id=%d", view_id)
    finally:
        db.close()

    # 若无活跃管线，注销 RECORDING 订阅者
    global _recording_subscribed
    if not _active_pipelines and _recording_subscribed:
        await event_bus.unsubscribe(RECORDING, _on_recording)
        _recording_subscribed = False
        logger.info("RECORDING subscriber unregistered")


async def stop_all() -> None:
    """停止所有活跃管线（Server 关闭时调用）。"""
    for view_id in list(_active_pipelines.keys()):
        await stop_pipeline(view_id)

"""Vision Pipeline 门户函数——被 API 层或其他 service 模块调用。

与 view_task.py / alert_task.py 同级，负责 AI 管线的启停编排。
"""

from __future__ import annotations

import logging

from src.service.vision_module.vision_pipeline import AIPipeline

logger = logging.getLogger(__name__)

# ── 活跃管线注册表 — {view_id: AIPipeline} ──
_active_pipelines: dict[int, AIPipeline] = {}


async def start_pipeline(view_id: int, video_id: int, video_name: str,
                         audio_id: int | None = None) -> bool:
    """启动指定 View 的 AI 推理管线。

    Returns:
        True if started successfully.
    """
    if view_id in _active_pipelines:
        logger.warning("Pipeline already running for view_id=%d", view_id)
        return False

    pipeline = AIPipeline()
    if not await pipeline.start(view_id, video_id, video_name, audio_id):
        return False

    _active_pipelines[view_id] = pipeline
    return True


async def stop_pipeline(view_id: int) -> None:
    """停止指定 View 的 AI 推理管线。"""
    pipeline = _active_pipelines.pop(view_id, None)
    if pipeline:
        await pipeline.stop()


async def stop_all() -> None:
    """停止所有活跃管线（Server 关闭时调用）。"""
    for view_id in list(_active_pipelines.keys()):
        await stop_pipeline(view_id)

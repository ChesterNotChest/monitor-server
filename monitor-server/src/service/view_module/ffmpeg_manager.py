"""FFmpeg 合流管理 —— 启动/停止/清理子进程。

Part A 完成后切换真实实现：
- ``src.network.rtmp.puller.build_pull_url`` 构建拉流地址
- ``src.network.rtmp.pusher.build_push_url`` 构建推流地址
"""

import asyncio
import atexit
import logging
import signal
from typing import Optional

logger = logging.getLogger(__name__)

# {view_id: asyncio.subprocess.Process}
active_processes: dict[int, asyncio.subprocess.Process] = {}


def _get_ffmpeg_cmd(view_id: int, video_id: int, audio_id: int) -> list[str]:
    """构建 FFmpeg 命令行参数。

    生产模式 → 推 SRS，debug 模式 → 推本地 RTMP 靶子。
    """
    from src.config import settings

    try:
        from src.network.rtmp.puller import build_pull_url
        from src.network.rtmp.pusher import build_push_url
        video_url = build_pull_url("video", video_id)
        audio_url = build_pull_url("audio", audio_id)
        push_url = build_push_url(view_id)
    except ImportError:
        # Part A 未就绪时的 fallback（开发阶段）
        video_url = f"rtmp://{settings.RTMP_HOST}:{settings.RTMP_PORT}/live/video_{video_id}"
        audio_url = f"rtmp://{settings.RTMP_HOST}:{settings.RTMP_PORT}/live/audio_{audio_id}"
        push_url = f"rtmp://127.0.0.1:1936/view/{view_id}"

    return [
        "ffmpeg",
        "-i", video_url,
        "-i", audio_url,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        push_url,
    ]


async def _start_ffmpeg_async(view_id: int, video_id: int, audio_id: int):
    """异步启动 FFmpeg 子进程。"""
    cmd = _get_ffmpeg_cmd(view_id, video_id, audio_id)
    logger.info("Starting FFmpeg for view %d: %s", view_id, " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    active_processes[view_id] = proc
    return proc


def start_merge(view_id: int, video_id: int, audio_id: int):
    """同步入口：启动 FFmpeg 合并推流。

    在已有 event loop 时直接 await，否则用 asyncio.run 桥接。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 无运行中的 loop——同步调用上下文
        asyncio.run(_start_ffmpeg_async(view_id, video_id, audio_id))
        return

    # 有运行中的 loop——创建 task
    loop.create_task(_start_ffmpeg_async(view_id, video_id, audio_id))


def stop_merge(view_id: int):
    """终止指定 View 的 FFmpeg 子进程。失败仅记日志。"""
    proc = active_processes.pop(view_id, None)
    if proc is None:
        return

    try:
        proc.send_signal(signal.SIGTERM)
        logger.info("FFmpeg for view %d terminated", view_id)
    except Exception as e:
        logger.warning("Failed to terminate FFmpeg for view %d: %s", view_id, e)


def cleanup_all():
    """终止所有 FFmpeg 子进程（注册到 atexit）。"""
    for view_id in list(active_processes.keys()):
        stop_merge(view_id)


atexit.register(cleanup_all)

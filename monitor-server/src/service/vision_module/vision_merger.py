"""合流推 SRS——FFmpeg 子进程合并标注 video frame pipe + raw audio RTMP pull。

标注帧以 rawvideo BGR24 格式通过 stdin pipe 推入 FFmpeg。
输出为 FLV 编码 RTMP push 到 SRS View 成品流。
"""

from __future__ import annotations

import asyncio
import logging
import shutil

import numpy as np

from src.config import settings

logger = logging.getLogger(__name__)


def _find_ffmpeg() -> str:
    """定位 ffmpeg 可执行文件。"""
    path = shutil.which("ffmpeg")
    if path:
        return path
    # Windows 常见路径
    for candidate in (r"C:\ffmpeg\bin\ffmpeg.exe",):
        import os
        if os.path.isfile(candidate):
            return candidate
    return "ffmpeg"


def _build_push_url(view_id: int) -> str:
    """构建 View 成品流 RTMP 推送地址。"""
    host = "127.0.0.1" if settings.DEBUG_WEB_STREAM else settings.SRS_HOST
    port = 1936 if settings.DEBUG_WEB_STREAM else settings.SRS_RTMP_PORT
    return f"rtmp://{host}:{port}/view/{view_id}"


def _build_audio_pull_url(audio_id: int) -> str:
    """构建 raw audio RTMP 拉流地址。"""
    host = "127.0.0.1" if settings.RTMP_DEBUG else settings.RTMP_HOST
    port = settings.RTMP_PORT
    return f"rtmp://{host}:{port}/live/audio_{audio_id}"


async def start_stream_merge(
    view_id: int,
    video_width: int,
    video_height: int,
    fps: int,
    audio_id: int | None = None,
) -> asyncio.subprocess.Process | None:
    """启动 FFmpeg 合并子进程。

    Args:
        view_id: View ID，用于构建推流 URL。
        video_width: 标注帧宽度。
        video_height: 标注帧高度。
        fps: 视频帧率。
        audio_id: 可选音频设备 ID；None 则仅推视频。

    Returns:
        FFmpeg subprocess，stdin 管道就绪；失败返回 None。
    """
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        logger.error("ffmpeg not found")
        return None

    push_url = _build_push_url(view_id)
    cmd: list[str] = [
        ffmpeg,
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{video_width}x{video_height}",
        "-r", str(fps),
        "-i", "pipe:0",
    ]

    # 音频源
    if audio_id is not None:
        audio_url = _build_audio_pull_url(audio_id)
        cmd += [
            "-i", audio_url,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
        ]
    else:
        cmd += ["-c:v", "libx264", "-preset", "ultrafast"]

    cmd += ["-f", "flv", push_url]

    logger.info("FFmpeg merge: %s", " ".join(cmd))
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        return proc
    except Exception:
        logger.exception("Failed to start FFmpeg merge")
        return None


async def push_frame(proc: asyncio.subprocess.Process, frame: np.ndarray) -> None:
    """写入一帧到 FFmpeg stdin pipe。frame 格式为 BGR24 numpy array。"""
    if proc.stdin is None or proc.returncode is not None:
        return
    try:
        proc.stdin.write(frame.tobytes())
    except BrokenPipeError:
        logger.warning("FFmpeg stdin pipe broken — stream ended")
    except Exception:
        logger.exception("Failed to push frame to FFmpeg")


async def stop_stream_merge(proc: asyncio.subprocess.Process) -> None:
    """终止 FFmpeg 子进程。"""
    try:
        if proc.stdin:
            proc.stdin.close()
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
    except ProcessLookupError:
        pass
    except Exception:
        logger.exception("Error stopping FFmpeg merge")

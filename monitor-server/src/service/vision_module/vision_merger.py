"""合流推流——FFmpeg 子进程：标注Video流编码后推送 RTMP。

pipe:0 (raw BGR24) → GPU/CPU 编码 → RTMP :1936/view/{view_id}

注意：当前为 video-only 模式。Audio流由独立的 raw merge 管线处理
（纯 RTMP→RTMP），或后续通过 SRS 合流。
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import sys

import numpy as np

from src.config import settings

logger = logging.getLogger(__name__)


def _find_ffmpeg() -> str:
    """定位 ffmpeg 可执行文件。"""
    path = shutil.which("ffmpeg")
    if path:
        return path
    for candidate in (r"C:\ffmpeg\bin\ffmpeg.exe",):
        import os
        if os.path.isfile(candidate):
            return candidate
    return "ffmpeg"


def _detect_encoder() -> str:
    """检测最优 H.264 编码器。

    Priority: h264_nvenc (NVENC GPU) → h264_mf (Windows Media Foundation) → libx264 (CPU).
    """
    ffmpeg = _find_ffmpeg()
    try:
        result = subprocess.run(
            [ffmpeg, "-encoders"], capture_output=True, text=True, timeout=10,
        )
        available = result.stdout + result.stderr
    except Exception:
        logger.warning("Failed to probe ffmpeg encoders, falling back to libx264")
        return "libx264"

    try:
        import torch
        if torch.cuda.is_available() and "h264_nvenc" in available:
            logger.info("Using encoder: h264_nvenc (NVENC GPU)")
            return "h264_nvenc"
    except ImportError:
        pass

    if sys.platform == "win32" and "h264_mf" in available:
        logger.info("Using encoder: h264_mf (Windows Media Foundation)")
        return "h264_mf"

    logger.info("Using encoder: libx264 (CPU)")
    return "libx264"


def _build_push_url(view_id: int) -> str:
    """构建最终合流 RTMP 推送地址。"""
    host = "127.0.0.1" if settings.DEBUG_WEB_STREAM else settings.SRS_HOST
    port = 1936 if settings.DEBUG_WEB_STREAM else settings.SRS_RTMP_PORT
    return f"rtmp://{host}:{port}/view/{view_id}"


async def start_stream_merge(
    view_id: int,
    video_width: int,
    video_height: int,
    fps: int,
    audio_id: int | None = None,
    audio_name: str = "",
) -> asyncio.subprocess.Process | None:
    """启动标注Video流推送 ffmpeg。返回 pipe:0 就绪的子进程。"""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        logger.error("ffmpeg not found")
        return None

    encoder = _detect_encoder()
    if encoder == "h264_nvenc":
        vcodec_args = ["-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll",
                       "-b:v", "2M", "-rc", "vbr"]
    else:
        vcodec_args = ["-c:v", encoder, "-preset", "ultrafast"]

    push_url = _build_push_url(view_id)
    cmd: list[str] = [
        ffmpeg,
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{video_width}x{video_height}", "-r", str(fps),
        "-i", "pipe:0",
        *vcodec_args,
        "-f", "flv", push_url,
    ]

    logger.info("FFmpeg merge: %s", " ".join(cmd))
    try:
        return await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception:
        logger.exception("Failed to start FFmpeg merge")
        return None


async def push_frame(proc: asyncio.subprocess.Process, frame: np.ndarray) -> None:
    """写入一帧到 ffmpeg stdin（同步 drain，确保帧到达编码器）。"""
    if proc.stdin is None or proc.returncode is not None:
        return
    try:
        proc.stdin.write(frame.tobytes())
        await proc.stdin.drain()
    except BrokenPipeError:
        logger.warning("FFmpeg stdin pipe broken — stream ended")
    except Exception:
        logger.exception("Failed to push frame to FFmpeg")


async def stop_stream_merge(proc: asyncio.subprocess.Process) -> None:
    """终止 ffmpeg 子进程。"""
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

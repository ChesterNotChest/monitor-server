"""合流推流——FFmpeg 子进程：标注Video流编码后推送 RTMP。

pipe:0 (raw BGR24 标注帧) → GPU/CPU 编码 → RTMP :1935/live/{view_id}

注意：当前为 video-only 模式。pipe:0 + RTMP 音频双输入会在 ffmpeg 中死锁
（详见 tools/mode2_e2e_playbook.md 坑 6）。音频通过 SRS 或后续两阶段方案合流。
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
    """构建 AI 标注流 RTMP 推送地址。

    调试模式走本地 RTMP（配置 RTMP_PORT，默认 1935，对应 SRS），
    生产模式走 SRS（SRS_HOST:SRS_RTMP_PORT）。
    """
    host = "127.0.0.1" if settings.DEBUG_WEB_STREAM else settings.SRS_HOST
    port = settings.RTMP_PORT if settings.DEBUG_WEB_STREAM else settings.SRS_RTMP_PORT
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
                       "-b:v", "2M", "-rc", "vbr",
                       "-zerolatency", "1", "-delay", "0",
                       "-g", "30"]  # 每秒一个关键帧，解决灰屏
    else:
        vcodec_args = ["-c:v", encoder, "-preset", "ultrafast", "-profile:v", "baseline"]

    push_url = _build_push_url(view_id)
    cmd: list[str] = [
        ffmpeg,
        "-vsync", "cfr",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{video_width}x{video_height}", "-r", str(fps),
        "-i", "pipe:0",
        "-pix_fmt", "yuv420p",
        *vcodec_args,
        "-flvflags", "no_duration_filesize",
        "-rtmp_live", "live",
        "-f", "flv", push_url,
    ]

    logger.info("[MERGE] FFmpeg cmd: %s", " ".join(cmd))
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        # 后台读取 ffmpeg stderr，避免管道满阻塞
        asyncio.create_task(_read_stderr(proc, view_id),
                            name=f"ffmpeg-stderr-view-{view_id}")
        return proc
    except Exception:
        logger.exception("Failed to start FFmpeg merge")
        return None


async def _read_stderr(proc: asyncio.subprocess.Process, view_id: int) -> None:
    """后台读取 ffmpeg stderr 并记录日志。首 30 行 INFO 级别以便诊断连接问题。"""
    if proc.stderr is None:
        return
    line_count = 0
    try:
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if not text:
                continue
            line_count += 1
            # 前 30 行或含错误关键词的用 INFO，其余 DEBUG
            is_important = (
                line_count <= 30
                or "error" in text.lower()
                or "failed" in text.lower()
                or "connection" in text.lower()
                or "refused" in text.lower()
                or "timeout" in text.lower()
                or "connected" in text.lower()
                or "speed" in text.lower()
                or "bitrate" in text.lower()
            )
            if is_important:
                logger.info("[ffmpeg-%d:L%d] %s", view_id, line_count, text)
            else:
                logger.debug("[ffmpeg-%d:L%d] %s", view_id, line_count, text)
    except Exception:
        logger.debug("ffmpeg stderr reader stopped for view_id=%d (L%d lines)", view_id, line_count)


# ── 可观测性 ──────────────────────────────────
_push_frame_count: int = 0
_push_last_log: float = 0.0

async def push_frame(proc: asyncio.subprocess.Process, frame: np.ndarray) -> None:
    """写入一帧到 ffmpeg stdin（同步 drain，确保帧到达编码器）。"""
    global _push_frame_count, _push_last_log
    if proc.stdin is None or proc.returncode is not None:
        return
    try:
        proc.stdin.write(frame.tobytes())
        await proc.stdin.drain()
        _push_frame_count += 1
        import time as _time
        now = _time.monotonic()
        if now - _push_last_log >= 5.0:
            fps = _push_frame_count / (now - _push_last_log) if _push_last_log > 0 else 0
            logger.info("[obs] push FPS: %.1f (frames=%d)", fps, _push_frame_count)
            _push_frame_count = 0
            _push_last_log = now
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

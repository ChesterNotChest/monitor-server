"""Manage FFmpeg merge subprocesses for monitor Views."""

from __future__ import annotations

import asyncio
import atexit
import logging
import signal

logger = logging.getLogger(__name__)

active_processes: dict[int, asyncio.subprocess.Process] = {}


def _get_merge_urls(
    view_id: int,
    video_id: int,
    audio_id: int,
    video_name: str | None = None,
    audio_name: str | None = None,
) -> tuple[str, str, str]:
    """Return video input, audio input, and push URLs for a View merge."""

    from src.config import settings

    try:
        from src.network.rtmp.puller import build_pull_url
        from src.network.rtmp.pusher import build_push_url

        video_url = build_pull_url(video_name or "video", "video", video_id)
        audio_url = build_pull_url(audio_name or "audio", "audio", audio_id)
        push_url = build_push_url(view_id)
    except ImportError:
        video_url = f"rtmp://{settings.RTMP_HOST}:{settings.RTMP_PORT}/live/video_{video_id}"
        audio_url = f"rtmp://{settings.RTMP_HOST}:{settings.RTMP_PORT}/live/audio_{audio_id}"
        push_url = f"rtmp://127.0.0.1:{settings.RTMP_PORT}/view/{view_id}"

    return video_url, audio_url, push_url


def _get_ffmpeg_cmd(
    view_id: int,
    video_id: int,
    audio_id: int,
    video_name: str | None = None,
    audio_name: str | None = None,
) -> list[str]:
    """Build the FFmpeg command used to merge raw audio/video RTMP streams."""

    video_url, audio_url, push_url = _get_merge_urls(
        view_id,
        video_id,
        audio_id,
        video_name,
        audio_name,
    )

    return [
        "ffmpeg",
        "-i",
        video_url,
        "-i",
        audio_url,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-f",
        "flv",
        push_url,
    ]


async def _start_ffmpeg_async(
    view_id: int,
    video_id: int,
    audio_id: int,
    video_name: str | None = None,
    audio_name: str | None = None,
) -> asyncio.subprocess.Process:
    """Start the merge FFmpeg subprocess."""

    cmd = _get_ffmpeg_cmd(view_id, video_id, audio_id, video_name, audio_name)
    logger.info("Starting FFmpeg for view %d: %s", view_id, " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    active_processes[view_id] = proc
    return proc


def start_merge(
    view_id: int,
    video_id: int,
    audio_id: int,
    video_name: str | None = None,
    audio_name: str | None = None,
    wait_for_inputs: bool = True,
    wait_timeout: float | None = None,
) -> tuple[bool, list[str]]:
    """Start a merge process after raw RTMP inputs are reachable."""

    if wait_for_inputs:
        from src.network.rtmp.puller import wait_for_streams

        video_url, audio_url, _ = _get_merge_urls(
            view_id,
            video_id,
            audio_id,
            video_name,
            audio_name,
        )
        ready, unavailable = wait_for_streams(
            [video_url, audio_url],
            timeout=wait_timeout,
        )
        if not ready:
            logger.warning(
                "Raw stream(s) unavailable for view %d: %s",
                view_id,
                unavailable,
            )
            return False, unavailable

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(
            _start_ffmpeg_async(view_id, video_id, audio_id, video_name, audio_name)
        )
        return True, []

    loop.create_task(
        _start_ffmpeg_async(view_id, video_id, audio_id, video_name, audio_name)
    )
    return True, []


def stop_merge(view_id: int) -> None:
    """Terminate the FFmpeg subprocess for a View."""

    proc = active_processes.pop(view_id, None)
    if proc is None:
        return

    try:
        proc.send_signal(signal.SIGTERM)
        logger.info("FFmpeg for view %d terminated", view_id)
    except Exception as exc:
        logger.warning("Failed to terminate FFmpeg for view %d: %s", view_id, exc)


def cleanup_all() -> None:
    """Terminate all active FFmpeg subprocesses."""

    for view_id in list(active_processes.keys()):
        stop_merge(view_id)


atexit.register(cleanup_all)

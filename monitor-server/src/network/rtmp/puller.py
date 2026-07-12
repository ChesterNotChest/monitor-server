"""Build and probe RTMP pull URLs for raw device streams."""

from __future__ import annotations

import shutil
import subprocess
import time

from src.config import settings


def build_pull_url(device_name: str, device_type: str, device_id: int) -> str:
    url_name = device_name.replace(" ", "_")
    stream_name = f"{url_name}_{device_type}_{device_id}"
    return f"rtmp://{settings.RTMP_HOST}:{settings.RTMP_PORT}/live/{stream_name}"


def is_stream_available(url: str, timeout: float | None = None) -> bool:
    """Return True when ffprobe can open an RTMP stream."""

    timeout = settings.STREAM_PROBE_TIMEOUT if timeout is None else timeout
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-rw_timeout",
                str(int(timeout * 1_000_000)),
                "-show_entries",
                "stream=codec_type",
                "-of",
                "compact=p=0:nk=1",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 1.0,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def wait_for_streams(
    urls: list[str],
    timeout: float | None = None,
    interval: float | None = None,
) -> tuple[bool, list[str]]:
    """Wait until every URL is reachable or return the unavailable URLs."""

    timeout = settings.STREAM_READY_TIMEOUT if timeout is None else timeout
    interval = settings.STREAM_READY_INTERVAL if interval is None else interval
    deadline = time.monotonic() + timeout
    unavailable = list(urls)

    while time.monotonic() <= deadline:
        unavailable = []
        for url in urls:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                unavailable.append(url)
                continue
            probe_timeout = min(settings.STREAM_PROBE_TIMEOUT, remaining)
            if not is_stream_available(url, timeout=probe_timeout):
                unavailable.append(url)
        if not unavailable:
            return True, []
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval, remaining))

    return False, unavailable

"""DEBUG_WEB_STREAM 本地 RTMP 靶子进程管理。"""

import atexit
import subprocess
from pathlib import Path

from src.config import settings

_process: subprocess.Popen | None = None


def start_debug_server(script_path: str | Path = "tools/rtmp_debug_server.js") -> subprocess.Popen | None:
    """在 DEBUG_WEB_STREAM 开启时启动本地 RTMP 靶子进程。"""

    global _process
    if not settings.DEBUG_WEB_STREAM:
        return None
    if _process is not None and _process.poll() is None:
        return _process

    script = Path(script_path)
    if not script.exists():
        return None

    _process = subprocess.Popen(["node", str(script)])
    return _process


def stop_debug_server() -> None:
    """停止已启动的本地 RTMP 靶子进程。"""

    global _process
    if _process is None or _process.poll() is not None:
        _process = None
        return

    _process.terminate()
    try:
        _process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _process.kill()
        _process.wait(timeout=5)
    finally:
        _process = None


atexit.register(stop_debug_server)

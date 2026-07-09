"""View 服务模块。
"""

from .lifecycle import get_ref_count, check_and_start_stream, check_and_stop_stream
from .ffmpeg_manager import start_merge, stop_merge, active_processes, cleanup_all

__all__ = [
    "get_ref_count",
    "check_and_start_stream",
    "check_and_stop_stream",
    "start_merge",
    "stop_merge",
    "active_processes",
    "cleanup_all",
]

"""
开发 / 生产启动入口。
"""

import os
import sys

# ── 必须在一切 import 之前初始化 CUDA 环境 ──────────────
# conda 环境中的 CUDA/cuDNN DLL 在 Library/bin 下，不在默认 PATH 中。
# Windows DLL 搜索路径用 PATH，必须在 import 前补上，否则 C 扩展
# 加载时会因找不到 DLL 而硬崩溃（非 Python 异常）。
_conda_lib_bin = os.path.join(sys.prefix, "Library", "bin")
if os.path.isdir(_conda_lib_bin) and _conda_lib_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _conda_lib_bin + os.pathsep + os.environ.get("PATH", "")

# 若配置为 CPU 模式，阻止 PyTorch / TensorFlow / OpenCV 发现并使用 GPU。
_yolo_device = os.environ.get("YOLO_DEVICE", "cpu")
if _yolo_device in ("", "cpu"):
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

# OpenCV FFmpeg 超时（必须在 cv2 首次 import 之前设置，否则不生效）
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "timeout;5000000")

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)

import uvicorn

from src.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

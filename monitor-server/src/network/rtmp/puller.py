"""构建从 SRS 拉取原始设备流的 RTMP 地址。"""

from src.config import settings


def build_pull_url(device_name: str, device_type: str, device_id: int) -> str:
    stream_name = f"{device_name}_{device_type}_{device_id}"
    return f"rtmp://{settings.RTMP_HOST}:{settings.RTMP_PORT}/live/{stream_name}"

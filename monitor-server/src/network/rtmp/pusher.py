"""构建合并后 View 流的推流与播放地址。"""

from src.config import settings

DEBUG_RTMP_HOST = "127.0.0.1"
DEBUG_RTMP_PORT = 1936


def _public_srs_host() -> str:
    return settings.SRS_PUBLIC_HOST or settings.SRS_HOST


def _public_srs_rtmp_port() -> int:
    return settings.SRS_PUBLIC_RTMP_PORT or settings.SRS_RTMP_PORT


def _public_srs_http_port() -> int:
    return settings.SRS_PUBLIC_HTTP_PORT or settings.SRS_HTTP_PORT


def build_push_url(view_id: int) -> str:
    if settings.DEBUG_WEB_STREAM:
        return f"rtmp://{DEBUG_RTMP_HOST}:{DEBUG_RTMP_PORT}/view/{view_id}"
    return f"rtmp://{settings.SRS_HOST}:{settings.SRS_RTMP_PORT}/view/{view_id}"


def build_play_urls(view_id: int) -> dict[str, str | None]:
    if settings.DEBUG_WEB_STREAM:
        return {
            "rtmp_url": f"rtmp://{DEBUG_RTMP_HOST}:{DEBUG_RTMP_PORT}/view/{view_id}",
            "flv_url": None,
            "webrtc_url": None,
        }

    public_host = _public_srs_host()
    public_rtmp_port = _public_srs_rtmp_port()
    public_http_port = _public_srs_http_port()

    return {
        "rtmp_url": f"rtmp://{public_host}:{public_rtmp_port}/view/{view_id}",
        "flv_url": f"http://{public_host}:{public_http_port}/view/{view_id}.flv",
        "webrtc_url": f"http://{public_host}:{public_http_port}/rtc/v1/whep/?app=view&stream={view_id}",
    }

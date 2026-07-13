"""构建合并后 View 流的推流与播放地址。"""

import logging

from src.config import settings

logger = logging.getLogger(__name__)

DEBUG_RTMP_HOST = "127.0.0.1"

# 调试模式下 RTMP 端口从配置读取（与 SRS listen 端口一致，默认 1935）
DEBUG_RTMP_PORT = settings.RTMP_PORT


def _public_srs_host() -> str:
    return settings.SRS_PUBLIC_HOST or settings.SRS_HOST


def _public_srs_rtmp_port() -> int:
    return settings.SRS_PUBLIC_RTMP_PORT or settings.SRS_RTMP_PORT


def _public_srs_http_port() -> int:
    return settings.SRS_PUBLIC_HTTP_PORT or settings.SRS_HTTP_PORT


def build_push_url(view_id: int) -> str:
    if settings.DEBUG_WEB_STREAM:
        url = f"rtmp://{DEBUG_RTMP_HOST}:{DEBUG_RTMP_PORT}/live/{view_id}"
    else:
        url = f"rtmp://{settings.SRS_HOST}:{settings.SRS_RTMP_PORT}/view/{view_id}"
    logger.info("[URL] build_push_url(view=%d) = %s | DEBUG_WEB_STREAM=%s",
                view_id, url, settings.DEBUG_WEB_STREAM)
    return url


def build_play_urls(view_id: int) -> dict[str, str | None]:
    logger.debug("[URL] build_play_urls(view=%d) | DEBUG_WEB_STREAM=%s | SRS_PUBLIC_HOST=%s",
                 view_id, settings.DEBUG_WEB_STREAM, settings.SRS_PUBLIC_HOST)

    if settings.DEBUG_WEB_STREAM:
        urls = {
            "rtmp_url": f"rtmp://{DEBUG_RTMP_HOST}:{DEBUG_RTMP_PORT}/view/{view_id}",
            "flv_url": None,
            "webrtc_url": None,
        }
        logger.warning("[URL] DEBUG_WEB_STREAM=true → webrtc_url=None, flv_url=None (view=%d)", view_id)
        return urls

    public_host = _public_srs_host()
    public_rtmp_port = _public_srs_rtmp_port()
    public_http_port = _public_srs_http_port()

    webrtc = f"http://{public_host}:1985/rtc/v1/whep/?app=view&stream={view_id}"

    urls = {
        "rtmp_url": f"rtmp://{public_host}:{public_rtmp_port}/view/{view_id}",
        "flv_url": f"http://{public_host}:{public_http_port}/view/{view_id}.flv",
        "webrtc_url": webrtc,
    }
    logger.debug("[URL] view=%d rtmp=%s webrtc=%s", view_id, urls["rtmp_url"], webrtc)
    return urls

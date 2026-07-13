"""钉钉群机器人 Webhook 渠道。"""

from __future__ import annotations

import json
import logging

import httpx

from .base import BaseChannel, NotificationPayload
from src.config import settings

logger = logging.getLogger(__name__)

# 速率限制：钉钉群机器人 20 条/分钟
_TOKEN_BUCKET_MAX = 20
_TOKEN_REFILL_RATE = 20 / 60.0  # tokens per second


class _RateLimiter:
    """令牌桶限流器 —— 无令牌时排队等待而非丢弃。"""

    def __init__(self, max_tokens: int = _TOKEN_BUCKET_MAX,
                 refill_rate: float = _TOKEN_REFILL_RATE) -> None:
        self._max = float(max_tokens)
        self._tokens = float(max_tokens)
        self._refill_rate = refill_rate
        import time
        self._last = time.monotonic()

    async def acquire(self) -> None:
        """等待直到获取到令牌。"""
        import asyncio
        while True:
            import time as _time
            now = _time.monotonic()
            self._tokens = min(self._max, self._tokens + (now - self._last) * self._refill_rate)
            self._last = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            await asyncio.sleep(0.5)  # 等半秒再试


_limiter = _RateLimiter()


class DingTalkWebhookChannel(BaseChannel):
    """钉钉群自定义机器人 Webhook 通知。"""

    async def send(self, payload: NotificationPayload, config: dict) -> bool:
        webhook_url = config.get("webhook_url", "") or settings.DINGTALK_WEBHOOK_URL
        if not webhook_url:
            logger.warning("DingTalkWebhookChannel: no webhook_url in config or settings")
            return False

        await _limiter.acquire()

        body = {
            "msgtype": "markdown",
            "markdown": {
                "title": payload.title,
                "text": payload.text,
            },
        }
        if payload.at_mobiles:
            # 同时用 atMobiles 和 atDingtalkIds 覆盖新旧版本钉钉
            body["at"] = {
                "atMobiles": payload.at_mobiles,
                "isAtAll": False,
            }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    webhook_url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    resp_data = resp.json()
                    if resp_data.get("errcode") == 0:
                        logger.info("DingTalk sent: alert=%s", payload.alert_id)
                        return True
                    else:
                        logger.error("DingTalk errcode=%s errmsg=%s",
                                     resp_data.get("errcode"), resp_data.get("errmsg"))
                        return False
                else:
                    logger.error("DingTalk HTTP %s: %s", resp.status_code, resp.text[:200])
                    return False
        except Exception:
            logger.exception("DingTalk send failed for alert %s", payload.alert_id)
            return False

    def validate_config(self, config: dict) -> bool:
        return bool(config.get("webhook_url") or settings.DINGTALK_WEBHOOK_URL)

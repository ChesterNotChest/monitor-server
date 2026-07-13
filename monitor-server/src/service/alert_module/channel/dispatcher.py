"""通知分发器 —— 根据 ResponseAction.channel 路由到对应渠道。"""

from __future__ import annotations

import json
import logging

from .base import BaseChannel, NotificationPayload
from .dingtalk_webhook import DingTalkWebhookChannel

logger = logging.getLogger(__name__)

_channels: dict[str, BaseChannel] = {
    "dingtalk_webhook": DingTalkWebhookChannel(),
}


def register_channel(name: str, channel: BaseChannel) -> None:
    """注册通知渠道（用于扩展自定义渠道）。"""
    _channels[name] = channel


async def dispatch(payload: NotificationPayload, response_actions: list) -> None:
    """遍历 response_actions，对每个有 channel 配置的执行 send。

    单个 channel 失败不阻塞其他 channel。
    """
    for ra in response_actions:
        channel_name = getattr(ra, "channel", None) if hasattr(ra, "channel") else None
        if not channel_name:
            continue

        channel = _channels.get(channel_name)
        if channel is None:
            logger.warning("Unknown channel: %s", channel_name)
            continue

        config = {}
        if hasattr(ra, "config_json") and ra.config_json:
            try:
                config = json.loads(ra.config_json)
            except json.JSONDecodeError:
                logger.warning("Invalid config_json for ResponseAction %s: %s", ra.id, ra.config_json)
                continue

        if not channel.validate_config(config):
            logger.warning("Invalid config for channel %s on ResponseAction %s", channel_name, ra.id)
            continue

        try:
            ok = await channel.send(payload, config)
            if not ok:
                logger.warning("Channel %s send failed for alert %s", channel_name, payload.alert_id)
        except Exception:
            logger.exception("Channel %s send error for alert %s", channel_name, payload.alert_id)

"""通知渠道包。"""

from .base import BaseChannel, NotificationPayload
from .dingtalk_webhook import DingTalkWebhookChannel
from .dispatcher import dispatch, register_channel

__all__ = [
    "BaseChannel",
    "NotificationPayload",
    "DingTalkWebhookChannel",
    "dispatch",
    "register_channel",
]

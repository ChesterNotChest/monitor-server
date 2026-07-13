"""通知渠道抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NotificationPayload:
    """通知消息的通用数据结构，各 channel 按需取用字段。"""
    title: str
    text: str                          # markdown 内容
    at_mobiles: list[str] | None = None  # 钉钉 @手机号
    alert_id: int | None = None
    view_name: str | None = None
    severity: str | None = None
    exception_name: str | None = None
    responder_names: list[str] | None = None
    ack_url: str | None = None         # 确认链接


class BaseChannel(ABC):
    """通知渠道的抽象基类。"""

    @abstractmethod
    async def send(self, payload: NotificationPayload, config: dict) -> bool:
        """发送通知，返回 True 表示成功。config 来自 ResponseAction.config_json。"""
        ...

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """验证 config 是否满足此渠道的最低要求。"""
        ...

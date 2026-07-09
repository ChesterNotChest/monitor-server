"""WebSocket 消息协议模型。"""

from .node_commands import (
    ConnectRequest,
    ConnectResponse,
    DeviceInfo,
    UpdateStreamRequest,
    UpdateStreamResponse,
)

__all__ = [
    "ConnectRequest",
    "ConnectResponse",
    "DeviceInfo",
    "UpdateStreamRequest",
    "UpdateStreamResponse",
]

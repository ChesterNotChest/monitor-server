"""浏览器告警 WebSocket —— 实时推送 SituationEvent 到前端。"""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.service.auth_task import verify_token

logger = logging.getLogger(__name__)


class AlertConnectionRegistry:
    """维护已认证浏览器 WebSocket 连接的注册表。"""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    def register(self, ws: WebSocket) -> None:
        self._connections.append(ws)

    def unregister(self, ws: WebSocket) -> None:
        try:
            self._connections.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """向所有已连接的浏览器广播告警消息。"""
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister(ws)

    @property
    def count(self) -> int:
        return len(self._connections)


alert_registry = AlertConnectionRegistry()


async def alert_websocket_endpoint(websocket: WebSocket) -> None:
    """处理浏览器告警 WebSocket 连接。通过查询参数中的 token 进行身份验证。"""
    await websocket.accept()

    # 从查询参数读取 JWT token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = verify_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub", "unknown")
    logger.info("[AlertWSS] Browser connected, user=%s", user_id)
    alert_registry.register(websocket)

    try:
        while True:
            # 保持连接活跃，接收客户端心跳/ping
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # 客户端可发送 ping，服务端回复 pong
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # 超时发送 ping 保持连接
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("[AlertWSS] Unexpected error")
    finally:
        alert_registry.unregister(websocket)
        logger.info("[AlertWSS] Browser disconnected, user=%s", user_id)

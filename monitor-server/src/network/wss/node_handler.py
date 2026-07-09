"""Node WebSocket 连接处理与命令发送。"""

from secrets import token_urlsafe
from typing import Any

from fastapi import Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.repository import device_repo, node_repo
from src.schema.wss import (
    ConnectRequest,
    ConnectResponse,
    DeviceInfo,
    UpdateStreamRequest,
    UpdateStreamResponse,
)


class NodeOfflineError(RuntimeError):
    """目标 Node 当前没有可用 WebSocket 连接。"""


class ConnectionRegistry:
    """维护 node_id 到 WebSocket 的内存映射，并提供命令发送能力。"""

    def __init__(self) -> None:
        self._connections: dict[int, WebSocket] = {}

    def register(self, node_id: int, websocket: WebSocket) -> None:
        self._connections[node_id] = websocket

    def unregister(self, node_id: int) -> None:
        self._connections.pop(node_id, None)

    def get(self, node_id: int) -> WebSocket | None:
        return self._connections.get(node_id)

    def is_online(self, node_id: int) -> bool:
        return node_id in self._connections

    async def send_command(
        self, node_id: int, request: UpdateStreamRequest
    ) -> UpdateStreamResponse:
        websocket = self.get(node_id)
        if websocket is None:
            raise NodeOfflineError(f"Node {node_id} is offline")

        await websocket.send_json(request.model_dump())
        payload = await websocket.receive_json()
        return UpdateStreamResponse.model_validate(payload)


registry = ConnectionRegistry()


async def node_websocket_endpoint(
    websocket: WebSocket, db: Session = Depends(get_db)
) -> None:
    """可直接注册到 FastAPI 的 Node WebSocket 端点。"""

    await handle_node_websocket(websocket, db)


async def handle_node_websocket(websocket: WebSocket, db: Session) -> None:
    """处理 Node 连接、认证、握手响应与断连清理。"""

    await websocket.accept()
    node_id: int | None = None
    try:
        payload: dict[str, Any] = await websocket.receive_json()
        connect_request = ConnectRequest.model_validate(payload)
        node = node_repo.get_by_token(db, connect_request.token)
        if node is None:
            await websocket.close(code=1008, reason="invalid token")
            return

        node_id = node.id
        node_repo.update_connection_status(db, node_id, True)
        registry.register(node_id, websocket)

        videos = [
            DeviceInfo.model_validate(video, from_attributes=True)
            for video in device_repo.get_videos_by_node(db, node_id)
        ]
        audios = [
            DeviceInfo.model_validate(audio, from_attributes=True)
            for audio in device_repo.get_audios_by_node(db, node_id)
        ]
        response = ConnectResponse(
            session_token=token_urlsafe(32),
            videos=videos,
            audios=audios,
        )
        await websocket.send_json(response.model_dump())

        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, ValidationError):
        pass
    finally:
        if node_id is not None:
            node_repo.update_connection_status(db, node_id, False)
            node_repo.reset_device_streaming_by_node(db, node_id)
            registry.unregister(node_id)

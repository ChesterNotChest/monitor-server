"""Node WebSocket 连接处理与命令发送。"""

import asyncio
from collections import deque
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
        self._loops: dict[int, asyncio.AbstractEventLoop] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._pending_responses: dict[int, deque[asyncio.Future[dict[str, Any]]]] = {}

    def register(self, node_id: int, websocket: WebSocket) -> None:
        self._connections[node_id] = websocket
        self._loops[node_id] = asyncio.get_running_loop()
        self._locks[node_id] = asyncio.Lock()
        self._pending_responses[node_id] = deque()

    def unregister(self, node_id: int) -> None:
        self._connections.pop(node_id, None)
        self._loops.pop(node_id, None)
        self._locks.pop(node_id, None)
        pending = self._pending_responses.pop(node_id, deque())
        while pending:
            future = pending.popleft()
            if not future.done():
                future.set_exception(NodeOfflineError(f"Node {node_id} is offline"))

    def get(self, node_id: int) -> WebSocket | None:
        return self._connections.get(node_id)

    def is_online(self, node_id: int) -> bool:
        return node_id in self._connections

    async def send_command(
        self, node_id: int, request: UpdateStreamRequest
    ) -> UpdateStreamResponse:
        loop = self._loops.get(node_id)
        if loop is None:
            raise NodeOfflineError(f"Node {node_id} is offline")

        if loop is asyncio.get_running_loop():
            return await self._send_command_on_owner_loop(node_id, request)

        future = asyncio.run_coroutine_threadsafe(
            self._send_command_on_owner_loop(node_id, request),
            loop,
        )
        return await asyncio.wrap_future(future)

    async def _send_command_on_owner_loop(
        self, node_id: int, request: UpdateStreamRequest
    ) -> UpdateStreamResponse:
        websocket = self.get(node_id)
        lock = self._locks.get(node_id)
        if websocket is None or lock is None:
            raise NodeOfflineError(f"Node {node_id} is offline")

        async with lock:
            future = asyncio.get_running_loop().create_future()
            self._pending_responses.setdefault(node_id, deque()).append(future)
            try:
                await websocket.send_json(request.model_dump())
                payload = await asyncio.wait_for(future, timeout=30)
            except WebSocketDisconnect as exc:
                self.unregister(node_id)
                raise NodeOfflineError(f"Node {node_id} is offline") from exc
            except asyncio.TimeoutError as exc:
                pending = self._pending_responses.get(node_id)
                if pending is not None:
                    try:
                        pending.remove(future)
                    except ValueError:
                        pass
                raise TimeoutError(f"Timed out waiting for Node {node_id} response") from exc
            return UpdateStreamResponse.model_validate(payload)

    def dispatch_inbound_message(self, node_id: int, payload: dict[str, Any]) -> bool:
        """Classify inbound Node messages and route command responses.

        Returns True when the message was consumed by the registry. Heartbeat
        messages are intentionally handled by the caller so it can update DB
        state using its request-scoped session.
        """
        message_type = payload.get("type")
        if message_type == "heartbeat":
            return False

        is_command_response = (
            message_type == "update_stream_response" or "success" in payload
        )
        if not is_command_response:
            return False

        pending = self._pending_responses.get(node_id)
        if not pending:
            return True

        future = pending.popleft()
        if not future.done():
            future.set_result(payload)
        return True


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
            inbound_payload: dict[str, Any] = await websocket.receive_json()
            if inbound_payload.get("type") == "heartbeat":
                node_repo.update_connection_status(db, node_id, True)
                continue
            registry.dispatch_inbound_message(node_id, inbound_payload)
    except (WebSocketDisconnect, ValidationError):
        pass
    finally:
        if node_id is not None:
            node_repo.update_connection_status(db, node_id, False)
            node_repo.reset_device_streaming_by_node(db, node_id)
            registry.unregister(node_id)

"""FastAPI WebSocket integration tests for the Node control channel."""

import asyncio

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.extensions import Base, get_db
from src.models import AudioDevice, Node, VideoDevice
from src.network.wss.node_handler import registry
from src.schema.wss import UpdateStreamRequest


def test_node_websocket_route_auth_returns_server_device_maps():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    node = Node(token="test-token")
    db.add(node)
    db.flush()
    video = VideoDevice(name="Integrated Camera", node_id=node.id)
    audio = AudioDevice(name="Microphone Array", node_id=node.id)
    db.add_all([video, audio])
    db.commit()
    node_id = node.id
    video_id = video.id
    audio_id = audio.id
    db.close()

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"token": "test-token"})
            auth_payload = websocket.receive_json()

            assert auth_payload["session_token"]
            assert auth_payload["videos"] == [{"id": video_id, "name": "Integrated Camera"}]
            assert auth_payload["audios"] == [{"id": audio_id, "name": "Microphone Array"}]
            assert registry.is_online(node_id)
    finally:
        app.dependency_overrides.pop(get_db, None)
        registry.unregister(node_id)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


class FakeNodeWebSocket:
    def __init__(self):
        self.sent_payloads = []

    async def send_json(self, payload):
        self.sent_payloads.append(payload)


@pytest.mark.asyncio
async def test_registry_send_command_emits_update_stream_and_reads_response():
    websocket = FakeNodeWebSocket()
    registry.register(123, websocket)
    try:
        command_task = asyncio.create_task(registry.send_command(
            123,
            UpdateStreamRequest(
                device_type="video",
                device_id=1,
                enable=True,
            ),
        ))
        await asyncio.sleep(0)
        registry.dispatch_inbound_message(123, {"type": "heartbeat"})
        registry.dispatch_inbound_message(
            123,
            {"type": "update_stream_response", "success": True, "message": "ok"},
        )
        response = await command_task
    finally:
        registry.unregister(123)

    assert websocket.sent_payloads == [
        {
            "command": "UPDATE_STREAM",
            "device_type": "video",
            "device_id": 1,
            "enable": True,
        }
    ]
    assert response.success is True
    assert response.message == "ok"


@pytest.mark.asyncio
async def test_registry_ignores_heartbeat_while_waiting_for_command_response():
    websocket = FakeNodeWebSocket()
    registry.register(456, websocket)
    try:
        command_task = asyncio.create_task(registry.send_command(
            456,
            UpdateStreamRequest(
                device_type="audio",
                device_id=2,
                enable=True,
            ),
        ))
        await asyncio.sleep(0)

        consumed = registry.dispatch_inbound_message(456, {"type": "heartbeat"})
        await asyncio.sleep(0)
        assert consumed is False
        assert command_task.done() is False

        registry.dispatch_inbound_message(456, {"success": True, "message": "ok"})
        response = await command_task
    finally:
        registry.unregister(456)

    assert response.success is True
    assert response.message == "ok"

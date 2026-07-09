"""Schema 层测试 —— 验证 Part A 的 Pydantic 请求/响应模型。

Part A 完成后这些测试会通过。
"""

import pytest


class TestConnectSchema:
    """14.3.1-14.3.2 WebSocket 连接握手 Schema 测试。"""

    def test_connect_request_serialization(self):
        """ConnectRequest(token="abc") → 序列化验证通过。"""
        # Part A 完成后:
        # from src.schema.wss.node_commands import ConnectRequest
        # req = ConnectRequest(token="abc")
        # d = req.model_dump()
        # assert d["token"] == "abc"
        pass

    def test_connect_response_deserialization(self):
        """ConnectResponse 反序列化 → 正确解析 session_token、videos、audios 字段。"""
        # Part A 完成后:
        # from src.schema.wss.node_commands import ConnectResponse
        # data = {"session_token": "sess-1", "videos": [...], "audios": [...]}
        # resp = ConnectResponse(**data)
        # assert resp.session_token == "sess-1"
        pass


class TestViewCreateSchema:
    """14.3.3-14.3.4 View 创建 Schema 测试。"""

    def test_view_create_request_valid(self):
        """ViewCreateRequest(audio_id=1, video_id=1) → 校验通过。"""
        # Part A 完成后:
        # from src.schema.http.view_schema import ViewCreateRequest
        # req = ViewCreateRequest(audio_id=1, video_id=1)
        # assert req.audio_id == 1
        pass

    def test_view_create_request_audio_none_fails(self):
        """ViewCreateRequest(audio_id=None, video_id=1) → 校验失败。"""
        # Part A 完成后:
        # with pytest.raises(ValidationError):
        #     ViewCreateRequest(audio_id=None, video_id=1)
        pass


class TestUpdateStreamSchema:
    """14.3.5 UpdateStreamRequest Schema 测试。"""

    def test_update_stream_request_serialization(self):
        """UpdateStreamRequest 序列化 → JSON 格式正确。"""
        # Part A 完成后:
        # from src.schema.wss.node_commands import UpdateStreamRequest
        # req = UpdateStreamRequest(device_type="video", device_id=5, enable=True)
        # d = req.model_dump()
        # assert d == {"command": "update_stream", "device_type": "video", "device_id": 5, "enable": True}
        pass

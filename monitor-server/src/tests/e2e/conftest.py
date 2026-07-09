"""E2E 测试专用 fixtures（预留）。

后续扩展点：
- TestClient(app) fixture（FastAPI TestClient）
- 预置测试数据 fixture（已注册的 Node、Device、View）
- Mock 外部服务 fixture（AI 检测服务、通知推送服务）
"""

# from fastapi.testclient import TestClient
# from src.app import app
# import pytest
#
# @pytest.fixture
# def client():
#     return TestClient(app)

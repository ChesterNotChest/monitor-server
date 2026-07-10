"""FenceEventType CRUD 测试 (tasks 15.5.1-15.5.4)。"""

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.constants import API_PREFIX, Role
from src.extensions import get_db
from src.repository.user_repo import UserRepo
from src.service.auth_task import hash_password

FENCE_URL = f"{API_PREFIX}/detection/fence-event-types"


@pytest.fixture
def client(db):
    """TestClient with manager auth (detection:manage)。"""
    repo = UserRepo(db)
    if repo.by_username("mgr_fence") is None:
        repo.create(username="mgr_fence", password_hash=hash_password("pw"),
                     role=Role.MANAGER, is_active=True)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    resp = client.post(f"{API_PREFIX}/auth/login", json={"username": "mgr_fence", "password": "pw"})
    token = resp.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    yield client
    app.dependency_overrides.clear()


class TestFenceEventTypeCRUD:
    def test_create_201(self, client):
        resp = client.post(FENCE_URL, json={"name": "ENTERED"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "ENTERED"

    def test_list_contains_entered(self, client):
        client.post(FENCE_URL, json={"name": "LOITERING"})
        resp = client.get(FENCE_URL)
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()]
        assert "LOITERING" in names

    def test_update_200(self, client):
        resp = client.post(FENCE_URL, json={"name": "OLD"})
        iid = resp.json()["id"]
        resp = client.put(f"{FENCE_URL}/{iid}", json={"name": "NEW"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "NEW"

    def test_delete_204(self, client):
        resp = client.post(FENCE_URL, json={"name": "TO_DEL"})
        iid = resp.json()["id"]
        resp = client.delete(f"{FENCE_URL}/{iid}")
        assert resp.status_code == 204

    def test_delete_nonexistent_404(self, client):
        resp = client.delete(f"{FENCE_URL}/99999")
        assert resp.status_code == 404

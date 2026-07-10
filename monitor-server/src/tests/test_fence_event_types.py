"""FenceEventType CRUD 测试。"""

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
    repo = UserRepo(db)
    if repo.by_username("mgr_fence") is None:
        repo.create(username="mgr_fence", password_hash=hash_password("pw"),
                     role=Role.MANAGER, is_active=True)
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    resp = c.post(f"{API_PREFIX}/auth/login", json={"username": "mgr_fence", "password": "pw"})
    c.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    yield c
    app.dependency_overrides.clear()


class TestFenceEventTypeCRUD:
    def test_create_201(self, client):
        resp = client.post(FENCE_URL, json={"name": "ENTERED"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "ENTERED"

    def test_list(self, client):
        client.post(FENCE_URL, json={"name": "LOITERING"})
        names = [i["name"] for i in client.get(FENCE_URL).json()]
        assert "LOITERING" in names

    def test_update_200(self, client):
        iid = client.post(FENCE_URL, json={"name": "OLD"}).json()["id"]
        resp = client.put(f"{FENCE_URL}/{iid}", json={"name": "NEW"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "NEW"

    def test_delete_204(self, client):
        iid = client.post(FENCE_URL, json={"name": "DEL"}).json()["id"]
        assert client.delete(f"{FENCE_URL}/{iid}").status_code == 204

    def test_delete_nonexistent_404(self, client):
        assert client.delete(f"{FENCE_URL}/99999").status_code == 404

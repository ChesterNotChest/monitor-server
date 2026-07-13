"""认证测试 —— 登录 / Token / 角色校验。"""

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.extensions import Base, SessionLocal
from src.service.auth_task import hash_password
from src.repository.user_repo import UserRepo
from src.constants import Role


@pytest.fixture
def client(db):
    """TestClient with DB-backed test user pre-created."""
    from src.repository.user_repo import UserRepo

    repo = UserRepo(db)
    existing = repo.by_username("test_admin")
    if existing is None:
        repo.create(
            username="test_admin",
            password_hash=hash_password("test123"),
            role=Role.OPERATOR,
            is_active=True,
        )
    # TestClient with overridden get_db
    from src.extensions import get_db

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestLogin:
    def test_login_success(self, client, db):
        resp = client.post("/api/v1/auth/login/", json={
            "username": "test_admin",
            "password": "test123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "test_admin"
        assert data["user"]["role"] == "operator"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/login/", json={
            "username": "test_admin",
            "password": "wrong",
        })
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, db):
        repo = UserRepo(db)
        repo.create(
            username="inactive_user",
            password_hash=hash_password("pw"),
            role=Role.SECURITY_GUARD,
            is_active=False,
        )
        resp = client.post("/api/v1/auth/login/", json={
            "username": "inactive_user",
            "password": "pw",
        })
        assert resp.status_code == 401


class TestMe:
    def test_me_with_valid_token(self, client):
        # Login
        resp = client.post("/api/v1/auth/login/", json={
            "username": "test_admin", "password": "test123",
        })
        token = resp.json()["access_token"]

        # GET /me
        resp = client.get("/api/v1/auth/me/", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == "test_admin"

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me/")
        assert resp.status_code == 401  # HTTPBearer returns 401 for missing header

    def test_me_with_invalid_token(self, client):
        resp = client.get("/api/v1/auth/me/", headers={
            "Authorization": "Bearer invalid.token.here",
        })
        assert resp.status_code == 401


class TestLogout:
    def test_logout_ok(self, client):
        resp = client.post("/api/v1/auth/logout/")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

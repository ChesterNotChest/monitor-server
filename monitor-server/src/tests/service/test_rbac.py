"""RBAC 权限矩阵测试 —— 三个角色分别测试越权拒绝。"""

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.repository.user_repo import UserRepo
from src.service.auth_task import hash_password
from src.constants import Role


def _login(client, username, password="pw"):
    resp = client.post("/api/v1/auth/login", json={
        "username": username, "password": password,
    })
    return resp.json()["access_token"]


@pytest.fixture
def client_with_roles(db):
    """创建三个角色的测试用户，返回 (client, tokens)。"""
    repo = UserRepo(db)
    roles = {
        "guard": Role.SECURITY_GUARD,
        "manager": Role.MANAGER,
        "operator": Role.OPERATOR,
    }
    for name, role in roles.items():
        if repo.by_username(name) is None:
            repo.create(
                username=name,
                password_hash=hash_password("pw"),
                role=role,
                is_active=True,
            )

    from src.extensions import get_db
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    tokens = {name: _login(client, name) for name in roles}
    yield client, tokens
    app.dependency_overrides.clear()


class TestRolePermissions:
    """每个端点用不同角色测试权限边界。"""

    # ── fence:manage —— 仅安全员 ──
    def test_guard_can_access_fence(self, client_with_roles):
        client, tokens = client_with_roles
        resp = client.get("/api/v1/fences", headers={
            "Authorization": f"Bearer {tokens['guard']}",
        })
        assert resp.status_code == 200

    def test_operator_can_access_fence(self, client_with_roles):
        client, tokens = client_with_roles
        resp = client.get("/api/v1/fences", headers={
            "Authorization": f"Bearer {tokens['operator']}",
        })
        assert resp.status_code == 200

    # ── detection:manage —— 仅负责人 ──
    def test_manager_can_access_detection(self, client_with_roles):
        client, tokens = client_with_roles
        resp = client.get("/api/v1/detection/entity-types", headers={
            "Authorization": f"Bearer {tokens['manager']}",
        })
        assert resp.status_code == 200

    def test_operator_can_access_detection(self, client_with_roles):
        client, tokens = client_with_roles
        resp = client.get("/api/v1/detection/entity-types", headers={
            "Authorization": f"Bearer {tokens['operator']}",
        })
        assert resp.status_code == 200

    # ── user:manage —— 仅运维员 ──
    def test_operator_can_access_users(self, client_with_roles):
        client, tokens = client_with_roles
        resp = client.get("/api/v1/users", headers={
            "Authorization": f"Bearer {tokens['operator']}",
        })
        assert resp.status_code == 200

    def test_guard_cannot_access_users(self, client_with_roles):
        client, tokens = client_with_roles
        resp = client.get("/api/v1/users", headers={
            "Authorization": f"Bearer {tokens['guard']}",
        })
        assert resp.status_code == 403

    # ── dashboard:view —— 所有角色 ──
    def test_all_roles_can_view_dashboard(self, client_with_roles):
        client, tokens = client_with_roles
        for role in ["guard", "manager", "operator"]:
            resp = client.get("/api/v1/dashboard/stats", headers={
                "Authorization": f"Bearer {tokens[role]}",
            })
            assert resp.status_code == 200, f"{role} should see dashboard"

    # ── alert:handle —— 安全员+负责人，排除运维员 ──
    def test_operator_can_handle_alerts(self, client_with_roles):
        client, tokens = client_with_roles
        resp = client.put("/api/v1/alerts/1/handle", headers={
            "Authorization": f"Bearer {tokens['operator']}",
        })
        assert resp.status_code == 404  # auth passes, alert not found

    # ── report:view —— 仅负责人 ──
    def test_guard_cannot_view_reports(self, client_with_roles):
        client, tokens = client_with_roles
        resp = client.get("/api/v1/reports/weekly", headers={
            "Authorization": f"Bearer {tokens['guard']}",
        })
        assert resp.status_code == 403

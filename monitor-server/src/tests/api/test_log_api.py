"""日志 API 端点测试。"""

from src.constants import API_PREFIX, LogType

LOG_URL = f"{API_PREFIX}/logs"


class TestLogAPI:
    def test_list_empty(self, client, admin_headers):
        resp = client.get(LOG_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_list_with_filter(self, client, admin_headers):
        resp = client.get(f"{LOG_URL}?log_type=1", headers=admin_headers)
        assert resp.status_code == 200

def test_mutating_api_writes_operation_log(client, db, admin_headers):
    from src.app import app

    class _SessionProxy:
        def __init__(self, session):
            self._session = session

        def __getattr__(self, name):
            return getattr(self._session, name)

        def close(self):
            pass

    app.state.audit_log_session_factory = lambda: _SessionProxy(db)
    try:
        resp = client.post(
            f"{API_PREFIX}/users/",
            params={"username": "audit-user", "password": "pw", "role": "manager"},
            headers=admin_headers,
        )
        assert resp.status_code == 201

        logs_resp = client.get(LOG_URL, headers=admin_headers)
        assert logs_resp.status_code == 200
        items = logs_resp.json()["items"]
        operation_logs = [item for item in items if item["log_type"] == int(LogType.OPERATION)]
        assert any("用户操作：创建/提交 users" == item["summary"] for item in operation_logs)
    finally:
        if hasattr(app.state, "audit_log_session_factory"):
            delattr(app.state, "audit_log_session_factory")

def test_successful_login_writes_operation_log(client, db):
    from src.constants import Role
    from src.repository.log_entry_repo import LogEntryRepo
    from src.repository.user_repo import UserRepo
    from src.service.auth_task import hash_password

    UserRepo(db).create(
        username="login-audit-user",
        password_hash=hash_password("pw"),
        role=Role.OPERATOR,
        is_active=True,
    )

    resp = client.post(
        f"{API_PREFIX}/auth/login/",
        json={"username": "login-audit-user", "password": "pw"},
    )

    assert resp.status_code == 200
    logs = LogEntryRepo(db).all(limit=20)
    assert any(
        entry.log_type == int(LogType.OPERATION)
        and entry.summary == "用户登录：login-audit-user"
        for entry in logs
    )


"""用户 API 端点测试。"""

from src.constants import API_PREFIX

USER_URL = f"{API_PREFIX}/users"


class TestUserAPI:
    def test_create(self, client, admin_headers):
        resp = client.post(USER_URL, params={
            "username": "张安保",
            "password": "test123",
            "role": "security_guard",
        }, headers=admin_headers)
        assert resp.status_code == 201
        assert resp.json()["username"] == "张安保"

    def test_list(self, client, admin_headers):
        resp = client.get(USER_URL, headers=admin_headers)
        assert resp.status_code == 200

    def test_duplicate(self, client, admin_headers):
        client.post(USER_URL, params={
            "username": "李管理",
            "password": "test123",
            "role": "manager",
        }, headers=admin_headers)
        resp = client.post(USER_URL, params={
            "username": "李管理",
            "password": "test123",
            "role": "manager",
        }, headers=admin_headers)
        assert resp.status_code == 409

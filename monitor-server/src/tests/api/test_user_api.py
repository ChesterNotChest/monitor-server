"""用户 API 端点测试。"""

from src.constants import API_PREFIX

USER_URL = f"{API_PREFIX}/users"


class TestUserAPI:
    def test_create(self, client):
        resp = client.post(USER_URL, json={"username": "张安保", "role": 1})
        assert resp.status_code == 201
        assert resp.json()["username"] == "张安保"

    def test_list(self, client):
        resp = client.get(USER_URL)
        assert resp.status_code == 200

    def test_duplicate(self, client):
        client.post(USER_URL, json={"username": "李管理", "role": 2})
        resp = client.post(USER_URL, json={"username": "李管理", "role": 2})
        assert resp.status_code == 409

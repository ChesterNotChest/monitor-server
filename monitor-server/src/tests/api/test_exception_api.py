"""异常规则 API 端点测试。"""

from src.constants import API_PREFIX

EXCEPTION_URL = f"{API_PREFIX}/exceptions"
GROUP_URL = f"{API_PREFIX}/alert-groups"


class TestExceptionAPI:
    def _setup_group(self, client, admin_headers):
        return client.post(GROUP_URL, json={"name": "测试告警组"}, headers=admin_headers).json()

    def test_create(self, client, admin_headers):
        g = self._setup_group(client, admin_headers)
        resp = client.post(EXCEPTION_URL, json={"name": "API测试异常", "severity": 3, "group_id": g["id"]}, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["severity"] == 3

    def test_list(self, client, admin_headers):
        resp = client.get(EXCEPTION_URL, headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_by_severity(self, client, admin_headers):
        resp = client.get(f"{EXCEPTION_URL}?severity=3", headers=admin_headers)
        assert resp.status_code == 200

    def test_update(self, client, admin_headers):
        g = self._setup_group(client, admin_headers)
        r = client.post(EXCEPTION_URL, json={"name": "信息异常", "severity": 1, "group_id": g["id"]}, headers=admin_headers)
        resp = client.put(
            f"{EXCEPTION_URL}/{r.json()['id']}",
            json={"name": "信息异常", "severity": 4, "group_id": g["id"]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["severity"] == 4

    def test_delete(self, client, admin_headers):
        g = self._setup_group(client, admin_headers)
        r = client.post(EXCEPTION_URL, json={"name": "测试告警", "severity": 2, "group_id": g["id"]}, headers=admin_headers)
        resp = client.delete(f"{EXCEPTION_URL}/{r.json()['id']}", headers=admin_headers)
        assert resp.status_code == 204

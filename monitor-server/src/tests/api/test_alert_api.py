"""告警分组 API 端点测试。"""

from src.constants import API_PREFIX

GROUP_URL = f"{API_PREFIX}/alert-groups"


class TestAlertGroupAPI:
    def test_create(self, client, admin_headers):
        resp = client.post(GROUP_URL, json={"name": "高优先级"}, headers=admin_headers)
        assert resp.status_code == 201

    def test_list(self, client, admin_headers):
        resp = client.get(GROUP_URL, headers=admin_headers)
        assert resp.status_code == 200

    def test_update(self, client, admin_headers):
        r = client.post(GROUP_URL, json={"name": "低优先级"}, headers=admin_headers)
        resp = client.put(f"{GROUP_URL}/{r.json()['id']}", json={"name": "测试组"}, headers=admin_headers)
        assert resp.status_code == 200

    def test_delete(self, client, admin_headers):
        r = client.post(GROUP_URL, json={"name": "待删除"}, headers=admin_headers)
        resp = client.delete(f"{GROUP_URL}/{r.json()['id']}", headers=admin_headers)
        assert resp.status_code == 204

"""日志 API 端点测试。"""

from src.constants import API_PREFIX

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

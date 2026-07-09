"""日志 API 端点测试。"""

from src.constants import API_PREFIX

LOG_URL = f"{API_PREFIX}/logs"


class TestLogAPI:
    def test_list_empty(self, client):
        resp = client.get(LOG_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_list_with_filter(self, client):
        resp = client.get(f"{LOG_URL}?log_type=1")
        assert resp.status_code == 200

    def test_stats(self, client):
        resp = client.get(f"{LOG_URL}/stats?group_by=log_type")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_stats_by_severity(self, client):
        resp = client.get(f"{LOG_URL}/stats?group_by=severity")
        assert resp.status_code == 200

"""事件日志与统计 API 端点测试。"""

from src.constants import API_PREFIX

EVENT_URL = f"{API_PREFIX}/events"


class TestEventAPI:
    def test_list_empty(self, client):
        resp = client.get(EVENT_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_with_view_id(self, client):
        resp = client.get(f"{EVENT_URL}?view_id=1")
        assert resp.status_code == 200

    def test_get_nonexistent(self, client):
        resp = client.get(f"{EVENT_URL}/99999")
        assert resp.status_code == 404


class TestStatsAPI:
    def test_by_exception(self, client):
        resp = client.get(f"{EVENT_URL}/stats/by-exception")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_trend_default(self, client):
        resp = client.get(f"{EVENT_URL}/stats/trend")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_trend_with_granularity(self, client):
        for g in ("hour", "day", "month"):
            resp = client.get(f"{EVENT_URL}/stats/trend?granularity={g}")
            assert resp.status_code == 200

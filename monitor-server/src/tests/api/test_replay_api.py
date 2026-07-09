"""录制回放 API 端点测试。"""

from src.constants import API_PREFIX


class TestReplayAPI:
    def test_list_recordings_empty(self, client):
        resp = client.get(f"{API_PREFIX}/views/1/recordings")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_recordings_with_time(self, client):
        resp = client.get(f"{API_PREFIX}/views/1/recordings?start=2026-01-01T00:00:00&end=2026-01-02T00:00:00")
        assert resp.status_code == 200

    def test_stream_nonexistent_recording(self, client):
        resp = client.get(f"{API_PREFIX}/recordings/99999/stream")
        assert resp.status_code == 404

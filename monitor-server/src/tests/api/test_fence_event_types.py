"""FenceEventType CRUD 测试 (tasks 15.5.1-15.5.4)。"""

from src.constants import API_PREFIX

FENCE_URL = f"{API_PREFIX}/detection/fence-event-types"


class TestFenceEventTypeCRUD:
    def test_create_201(self, client, admin_headers):
        resp = client.post(FENCE_URL, json={"name": "ENTERED"}, headers=admin_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "ENTERED"

    def test_list_contains_entered(self, client, admin_headers):
        client.post(FENCE_URL, json={"name": "LOITERING"}, headers=admin_headers)
        resp = client.get(FENCE_URL, headers=admin_headers)
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()]
        assert "LOITERING" in names

    def test_update_200(self, client, admin_headers):
        resp = client.post(FENCE_URL, json={"name": "OLD"}, headers=admin_headers)
        iid = resp.json()["id"]
        resp = client.put(f"{FENCE_URL}/{iid}", json={"name": "NEW"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "NEW"

    def test_delete_204(self, client, admin_headers):
        resp = client.post(FENCE_URL, json={"name": "TO_DEL"}, headers=admin_headers)
        iid = resp.json()["id"]
        resp = client.delete(f"{FENCE_URL}/{iid}", headers=admin_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_404(self, client, admin_headers):
        resp = client.delete(f"{FENCE_URL}/99999", headers=admin_headers)
        assert resp.status_code == 404

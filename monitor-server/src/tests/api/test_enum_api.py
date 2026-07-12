"""枚举类型 API 端点测试。"""

from src.constants import API_PREFIX

ENTITY_URL = f"{API_PREFIX}/detection/entity-types"
ACTION_URL = f"{API_PREFIX}/detection/action-types"
SOUND_URL = f"{API_PREFIX}/detection/sound-types"


class TestEntityTypeAPI:
    def test_create(self, client, admin_headers):
        resp = client.post(ENTITY_URL, json={"name": "person"}, headers=admin_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "person"

    def test_list(self, client, admin_headers):
        resp = client.get(ENTITY_URL, headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_update(self, client, admin_headers):
        r = client.post(ENTITY_URL, json={"name": "dog"}, headers=admin_headers)
        pid = r.json()["id"]
        resp = client.put(f"{ENTITY_URL}/{pid}", json={"name": "cat"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "cat"

    def test_delete(self, client, admin_headers):
        r = client.post(ENTITY_URL, json={"name": "bird"}, headers=admin_headers)
        pid = r.json()["id"]
        resp = client.delete(f"{ENTITY_URL}/{pid}", headers=admin_headers)
        assert resp.status_code == 204


class TestActionTypeAPI:
    def test_create(self, client, admin_headers):
        resp = client.post(ACTION_URL, json={"name": "walking"}, headers=admin_headers)
        assert resp.status_code == 201

    def test_list(self, client, admin_headers):
        resp = client.get(ACTION_URL, headers=admin_headers)
        assert resp.status_code == 200

    def test_delete(self, client, admin_headers):
        r = client.post(ACTION_URL, json={"name": "running"}, headers=admin_headers)
        resp = client.delete(f"{ACTION_URL}/{r.json()['id']}", headers=admin_headers)
        assert resp.status_code == 204


class TestSoundTypeAPI:
    def test_create(self, client, admin_headers):
        resp = client.post(SOUND_URL, json={"name": "gunshot"}, headers=admin_headers)
        assert resp.status_code == 201

    def test_list(self, client, admin_headers):
        resp = client.get(SOUND_URL, headers=admin_headers)
        assert resp.status_code == 200

    def test_delete(self, client, admin_headers):
        r = client.post(SOUND_URL, json={"name": "scream"}, headers=admin_headers)
        resp = client.delete(f"{SOUND_URL}/{r.json()['id']}", headers=admin_headers)
        assert resp.status_code == 204

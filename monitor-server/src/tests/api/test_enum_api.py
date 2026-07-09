"""枚举类型 API 端点测试。"""

from src.constants import API_PREFIX

ENTITY_URL = f"{API_PREFIX}/entity-types"
ACTION_URL = f"{API_PREFIX}/action-types"
SOUND_URL = f"{API_PREFIX}/sound-types"


class TestEntityTypeAPI:
    def test_create(self, client):
        resp = client.post(ENTITY_URL, json={"name": "person"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "person"

    def test_list(self, client):
        resp = client.get(ENTITY_URL)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_one(self, client):
        r = client.post(ENTITY_URL, json={"name": "car"})
        pid = r.json()["id"]
        resp = client.get(f"{ENTITY_URL}/{pid}")
        assert resp.status_code == 200

    def test_get_nonexistent(self, client):
        resp = client.get(f"{ENTITY_URL}/99999")
        assert resp.status_code == 404

    def test_update(self, client):
        r = client.post(ENTITY_URL, json={"name": "dog"})
        pid = r.json()["id"]
        resp = client.put(f"{ENTITY_URL}/{pid}", json={"name": "cat"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "cat"

    def test_delete(self, client):
        r = client.post(ENTITY_URL, json={"name": "bird"})
        pid = r.json()["id"]
        resp = client.delete(f"{ENTITY_URL}/{pid}")
        assert resp.status_code == 204

    def test_duplicate(self, client):
        client.post(ENTITY_URL, json={"name": "unique_entity"})
        resp = client.post(ENTITY_URL, json={"name": "unique_entity"})
        assert resp.status_code == 409


class TestActionTypeAPI:
    def test_create(self, client):
        resp = client.post(ACTION_URL, json={"name": "walking"})
        assert resp.status_code == 201

    def test_list(self, client):
        resp = client.get(ACTION_URL)
        assert resp.status_code == 200

    def test_delete(self, client):
        r = client.post(ACTION_URL, json={"name": "running"})
        resp = client.delete(f"{ACTION_URL}/{r.json()['id']}")
        assert resp.status_code == 204


class TestSoundTypeAPI:
    def test_create(self, client):
        resp = client.post(SOUND_URL, json={"name": "gunshot"})
        assert resp.status_code == 201

    def test_list(self, client):
        resp = client.get(SOUND_URL)
        assert resp.status_code == 200

    def test_delete(self, client):
        r = client.post(SOUND_URL, json={"name": "scream"})
        resp = client.delete(f"{SOUND_URL}/{r.json()['id']}")
        assert resp.status_code == 204

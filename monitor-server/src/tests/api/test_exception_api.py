"""异常规则 API 端点测试。"""

from src.constants import API_PREFIX

EXCEPTION_URL = f"{API_PREFIX}/exceptions"
ENTITY_URL = f"{API_PREFIX}/entity-types"
ACTION_URL = f"{API_PREFIX}/action-types"
SOUND_URL = f"{API_PREFIX}/sound-types"
GROUP_URL = f"{API_PREFIX}/alert-groups"


class TestExceptionAPI:
    def _setup_group(self, client):
        return client.post(GROUP_URL, json={"name": "测试告警组"}).json()

    def test_create(self, client):
        g = self._setup_group(client)
        resp = client.post(EXCEPTION_URL, json={"name": "API测试异常", "severity": 3, "group_id": g["id"]})
        assert resp.status_code == 201
        data = resp.json()
        assert data["severity"] == 3  # CRITICAL
        assert data["group_id"] == g["id"]

    def test_list(self, client):
        resp = client.get(EXCEPTION_URL)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_by_severity(self, client):
        resp = client.get(f"{EXCEPTION_URL}?severity=3")
        assert resp.status_code == 200

    def test_get_one(self, client):
        g = self._setup_group(client)
        r = client.post(EXCEPTION_URL, json={"name": "测试告警", "severity": 2, "group_id": g["id"]})
        resp = client.get(f"{EXCEPTION_URL}/{r.json()['id']}")
        assert resp.status_code == 200

    def test_update(self, client):
        g = self._setup_group(client)
        r = client.post(EXCEPTION_URL, json={"name": "信息异常", "severity": 1, "group_id": g["id"]})
        resp = client.put(
            f"{EXCEPTION_URL}/{r.json()['id']}",
            json={"severity": 4, "group_id": g["id"]},
        )
        assert resp.status_code == 200
        assert resp.json()["severity"] == 4

    def test_delete(self, client):
        g = self._setup_group(client)
        r = client.post(EXCEPTION_URL, json={"name": "测试告警", "severity": 2, "group_id": g["id"]})
        resp = client.delete(f"{EXCEPTION_URL}/{r.json()['id']}")
        assert resp.status_code == 204


class TestBinding:
    def _setup(self, client):
        g = client.post(GROUP_URL, json={"name": "M2M测试"}).json()
        exc = client.post(EXCEPTION_URL, json={"name": "API测试异常", "severity": 3, "group_id": g["id"]}).json()
        return exc

    def test_bind_entity(self, client):
        exc = self._setup(client)
        ent = client.post(ENTITY_URL, json={"name": "person_m2m"}).json()
        resp = client.post(f"{EXCEPTION_URL}/{exc['id']}/entities", json={"entity_id": ent["id"]})
        assert resp.status_code == 200

    def test_unbind_entity(self, client):
        exc = self._setup(client)
        ent = client.post(ENTITY_URL, json={"name": "car_m2m"}).json()
        client.post(f"{EXCEPTION_URL}/{exc['id']}/entities", json={"entity_id": ent["id"]})
        resp = client.delete(f"{EXCEPTION_URL}/{exc['id']}/entities/{ent['id']}")
        assert resp.status_code == 204

    def test_bind_action(self, client):
        exc = self._setup(client)
        act = client.post(ACTION_URL, json={"name": "fighting_m2m"}).json()
        resp = client.post(f"{EXCEPTION_URL}/{exc['id']}/actions", json={"action_id": act["id"]})
        assert resp.status_code == 200

    def test_bind_sound(self, client):
        exc = self._setup(client)
        snd = client.post(SOUND_URL, json={"name": "explosion_m2m"}).json()
        resp = client.post(f"{EXCEPTION_URL}/{exc['id']}/sounds", json={"sound_id": snd["id"]})
        assert resp.status_code == 200

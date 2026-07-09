"""告警分组与响应动作 API 端点测试。"""

from src.constants import API_PREFIX

RESPONSE_URL = f"{API_PREFIX}/response-actions"
GROUP_URL = f"{API_PREFIX}/alert-groups"


class TestResponseActionAPI:
    def test_create(self, client):
        resp = client.post(RESPONSE_URL, json={"name": "trigger_recording"})
        assert resp.status_code == 201

    def test_list(self, client):
        resp = client.get(RESPONSE_URL)
        assert resp.status_code == 200

    def test_delete(self, client):
        r = client.post(RESPONSE_URL, json={"name": "send_email"})
        resp = client.delete(f"{RESPONSE_URL}/{r.json()['id']}")
        assert resp.status_code == 204

    def test_duplicate(self, client):
        client.post(RESPONSE_URL, json={"name": "unique_response"})
        resp = client.post(RESPONSE_URL, json={"name": "unique_response"})
        assert resp.status_code == 409


class TestAlertGroupAPI:
    def test_create(self, client):
        resp = client.post(GROUP_URL, json={"name": "高优先级"})
        assert resp.status_code == 201

    def test_list(self, client):
        resp = client.get(GROUP_URL)
        assert resp.status_code == 200

    def test_get_one(self, client):
        r = client.post(GROUP_URL, json={"name": "中优先级"})
        resp = client.get(f"{GROUP_URL}/{r.json()['id']}")
        assert resp.status_code == 200

    def test_update(self, client):
        r = client.post(GROUP_URL, json={"name": "低优先级"})
        resp = client.put(f"{GROUP_URL}/{r.json()['id']}", json={"name": "测试组"})
        assert resp.status_code == 200

    def test_delete(self, client):
        r = client.post(GROUP_URL, json={"name": "待删除"})
        resp = client.delete(f"{GROUP_URL}/{r.json()['id']}")
        assert resp.status_code == 204


class TestBinding:
    def test_bind_and_unbind(self, client):
        g = client.post(GROUP_URL, json={"name": "绑定测试"}).json()
        r = client.post(RESPONSE_URL, json={"name": "notify_bind"}).json()

        # bind
        resp = client.post(f"{GROUP_URL}/{g['id']}/responses", json={"response_id": r["id"]})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # idempotent bind
        resp2 = client.post(f"{GROUP_URL}/{g['id']}/responses", json={"response_id": r["id"]})
        assert resp2.status_code == 200

        # unbind
        resp3 = client.delete(f"{GROUP_URL}/{g['id']}/responses/{r['id']}")
        assert resp3.status_code == 204

    def test_bind_nonexistent_group(self, client):
        r = client.post(RESPONSE_URL, json={"name": "orphan_resp"}).json()
        resp = client.post(f"{GROUP_URL}/99999/responses", json={"response_id": r["id"]})
        assert resp.status_code == 404

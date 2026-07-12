"""NamedPerson API 端点测试。"""

from io import BytesIO

from src.constants import API_PREFIX

PERSONS_URL = f"{API_PREFIX}/persons"


class TestCreatePerson:
    def test_create_success(self, client):
        resp = client.post(PERSONS_URL, json={"name": "张三"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "张三"
        assert data["id"] is not None

    def test_create_empty_name(self, client):
        resp = client.post(PERSONS_URL, json={"name": ""})
        assert resp.status_code == 422

    def test_create_duplicate_name(self, client):
        resp1 = client.post(PERSONS_URL, json={"name": "唯一姓名"})
        assert resp1.status_code == 201
        resp2 = client.post(PERSONS_URL, json={"name": "唯一姓名"})
        assert resp2.status_code == 409


class TestListPersons:
    def test_list_default_pagination(self, client):
        for i in range(3):
            client.post(PERSONS_URL, json={"name": f"列表测试_{i}"})
        resp = client.get(PERSONS_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3

    def test_list_custom_pagination(self, client):
        for i in range(5):
            client.post(PERSONS_URL, json={"name": f"分页测试_{i}"})
        resp = client.get(f"{PERSONS_URL}?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2


class TestGetPerson:
    def test_get_existing(self, client):
        resp = client.post(PERSONS_URL, json={"name": "详情测试"})
        pid = resp.json()["id"]
        resp2 = client.get(f"{PERSONS_URL}/{pid}")
        assert resp2.status_code == 200
        assert resp2.json()["name"] == "详情测试"

    def test_get_nonexistent(self, client):
        resp = client.get(f"{PERSONS_URL}/99999")
        assert resp.status_code == 404


class TestUpdatePerson:
    def test_update_name(self, client):
        resp = client.post(PERSONS_URL, json={"name": "旧姓名"})
        pid = resp.json()["id"]
        resp2 = client.put(f"{PERSONS_URL}/{pid}", json={"name": "新姓名"})
        assert resp2.status_code == 200
        assert resp2.json()["name"] == "新姓名"

    def test_update_nonexistent(self, client):
        resp = client.put(f"{PERSONS_URL}/99999", json={"name": "不存在"})
        assert resp.status_code == 404

    def test_update_to_existing_name(self, client):
        client.post(PERSONS_URL, json={"name": "名字A"})
        resp = client.post(PERSONS_URL, json={"name": "名字B"})
        pid_b = resp.json()["id"]
        resp2 = client.put(f"{PERSONS_URL}/{pid_b}", json={"name": "名字A"})
        assert resp2.status_code == 409


class TestDeletePerson:
    def test_delete_existing(self, client):
        resp = client.post(PERSONS_URL, json={"name": "待删除"})
        pid = resp.json()["id"]
        resp2 = client.delete(f"{PERSONS_URL}/{pid}")
        assert resp2.status_code == 204
        resp3 = client.get(f"{PERSONS_URL}/{pid}")
        assert resp3.status_code == 404

    def test_delete_nonexistent(self, client):
        resp = client.delete(f"{PERSONS_URL}/99999")
        assert resp.status_code == 404


class TestUploadAvatar:
    def test_upload_avatar_to_existing_person(self, client):
        resp = client.post(PERSONS_URL, json={"name": "头像用户"})
        pid = resp.json()["id"]
        fake_image = BytesIO(b"fake-jpeg-data")
        resp2 = client.post(
            f"{PERSONS_URL}/{pid}/avatar",
            files={"avatar": ("face.jpg", fake_image, "image/jpeg")},
        )
        assert resp2.status_code == 200
        result = resp2.json()
        assert result["avatar_path"] is not None
        assert "person_" in result["avatar_path"]

    def test_upload_avatar_to_nonexistent(self, client):
        fake_image = BytesIO(b"fake")
        resp = client.post(
            f"{PERSONS_URL}/99999/avatar",
            files={"avatar": ("face.jpg", fake_image, "image/jpeg")},
        )
        assert resp.status_code == 404

    def test_upload_invalid_file_type(self, client):
        resp = client.post(PERSONS_URL, json={"name": "格式测试"})
        pid = resp.json()["id"]
        fake_text = BytesIO(b"not-an-image")
        resp2 = client.post(
            f"{PERSONS_URL}/{pid}/avatar",
            files={"avatar": ("readme.txt", fake_text, "text/plain")},
        )
        assert resp2.status_code == 422

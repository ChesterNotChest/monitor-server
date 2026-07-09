"""NamedPersonRepo 冒烟测试。"""

from src.repository.named_person_repo import NamedPersonRepo


class TestNamedPersonRepo:
    def test_create_and_get(self, db):
        repo = NamedPersonRepo(db)
        np = repo.create(avatar_path="/tmp/face.png", feat_json_id="feat-001")
        assert np.id is not None
        fetched = repo.get(np.id)
        assert fetched.avatar_path == "/tmp/face.png"
        assert fetched.feat_json_id == "feat-001"

    def test_create_with_nullable_fields(self, db):
        repo = NamedPersonRepo(db)
        np = repo.create()
        assert np.id is not None
        assert np.avatar_path is None
        assert np.feat_json_id is None

    def test_delete(self, db):
        repo = NamedPersonRepo(db)
        np = repo.create(avatar_path="/tmp/del.png")
        assert repo.delete(np.id) is True
        assert repo.get(np.id) is None

    def test_delete_nonexistent(self, db):
        repo = NamedPersonRepo(db)
        assert repo.delete(99999) is False

    def test_count_and_paginate(self, db):
        repo = NamedPersonRepo(db)
        for i in range(4):
            repo.create(avatar_path=f"/tmp/{i}.png")
        assert repo.count() == 4
        items, total = repo.paginate(page=1, page_size=2)
        assert len(items) == 2
        assert total == 4

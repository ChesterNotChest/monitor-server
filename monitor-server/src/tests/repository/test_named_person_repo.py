"""NamedPersonRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.named_person_repo import NamedPersonRepo


class TestNamedPersonRepo:
    def test_create_and_get(self, db):
        repo = NamedPersonRepo(db)
        np = repo.create(name="张三", avatar_path="/tmp/face.png", feat_json_id="feat-001")
        assert np.id is not None
        fetched = repo.get(np.id)
        assert fetched.name == "张三"
        assert fetched.avatar_path == "/tmp/face.png"
        assert fetched.feat_json_id == "feat-001"

    def test_create_with_nullable_fields(self, db):
        repo = NamedPersonRepo(db)
        np = repo.create(name="李四")
        assert np.id is not None
        assert np.name == "李四"
        assert np.avatar_path is None
        assert np.feat_json_id is None

    def test_name_unique_constraint(self, db):
        repo = NamedPersonRepo(db)
        repo.create(name="王五")
        with pytest.raises(IntegrityError):
            repo.create(name="王五")

    def test_delete(self, db):
        repo = NamedPersonRepo(db)
        np = repo.create(name="赵六", avatar_path="/tmp/del.png")
        assert repo.delete(np.id) is True
        assert repo.get(np.id) is None

    def test_delete_nonexistent(self, db):
        repo = NamedPersonRepo(db)
        assert repo.delete(99999) is False

    def test_count_and_paginate(self, db):
        repo = NamedPersonRepo(db)
        for i in range(4):
            repo.create(name=f"用户_{i}", avatar_path=f"/tmp/{i}.png")
        assert repo.count() == 4
        items, total = repo.paginate(page=1, page_size=2)
        assert len(items) == 2
        assert total == 4

    def test_update(self, db):
        repo = NamedPersonRepo(db)
        np = repo.create(name="测试用户")
        updated = repo.update(np.id, name="新名称", avatar_path="/new/path.png")
        assert updated is not None
        assert updated.name == "新名称"
        assert updated.avatar_path == "/new/path.png"

    def test_update_partial(self, db):
        repo = NamedPersonRepo(db)
        np = repo.create(name="部分更新", avatar_path="/old/path.png")
        updated = repo.update(np.id, name="新名称2")
        assert updated is not None
        assert updated.name == "新名称2"
        assert updated.avatar_path == "/old/path.png"  # unchanged

    def test_update_nonexistent(self, db):
        repo = NamedPersonRepo(db)
        assert repo.update(99999, name="不存在") is None

    def test_find_by_name(self, db):
        repo = NamedPersonRepo(db)
        repo.create(name="查找测试")
        found = repo.find_by_name("查找测试")
        assert found is not None
        assert found.name == "查找测试"

    def test_find_by_name_not_found(self, db):
        repo = NamedPersonRepo(db)
        assert repo.find_by_name("不存在的名字") is None

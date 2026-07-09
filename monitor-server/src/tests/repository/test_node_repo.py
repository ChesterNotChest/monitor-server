"""NodeRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.node_repo import NodeRepo


class TestNodeRepo:
    def test_create_and_get(self, db):
        repo = NodeRepo(db)
        node = repo.create(token="tok-001")
        assert node.id is not None
        fetched = repo.get(node.id)
        assert fetched.token == "tok-001"

    def test_by_token_found(self, db):
        repo = NodeRepo(db)
        repo.create(token="tok-abc")
        assert repo.by_token("tok-abc") is not None

    def test_by_token_not_found(self, db):
        repo = NodeRepo(db)
        assert repo.by_token("nonexistent") is None

    def test_delete(self, db):
        repo = NodeRepo(db)
        node = repo.create(token="tok-del")
        assert repo.delete(node.id) is True
        assert repo.get(node.id) is None

    def test_delete_nonexistent(self, db):
        repo = NodeRepo(db)
        assert repo.delete(99999) is False

    def test_get_nonexistent(self, db):
        repo = NodeRepo(db)
        assert repo.get(99999) is None

    def test_exists(self, db):
        repo = NodeRepo(db)
        node = repo.create(token="tok-exists")
        assert repo.exists(node.id) is True
        assert repo.exists(99999) is False

    def test_count_and_paginate(self, db):
        repo = NodeRepo(db)
        for i in range(5):
            repo.create(token=f"tok-pag-{i}")
        assert repo.count() == 5
        items, total = repo.paginate(page=1, page_size=3)
        assert len(items) == 3
        assert total == 5

    def test_unique_token_violation(self, db):
        repo = NodeRepo(db)
        repo.create(token="dup-tok")
        with pytest.raises(IntegrityError):
            repo.create(token="dup-tok")

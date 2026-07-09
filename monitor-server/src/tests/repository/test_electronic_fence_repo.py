"""ElectronicFenceRepo 冒烟测试。"""

from src.repository.electronic_fence_repo import ElectronicFenceRepo


class TestElectronicFenceRepo:
    def test_create_and_get(self, db):
        repo = ElectronicFenceRepo(db)
        ef = repo.create(coords="[[116.3,39.9],[116.4,40.0]]")
        assert ef.id is not None
        assert repo.get(ef.id).coords == "[[116.3,39.9],[116.4,40.0]]"

    def test_delete(self, db):
        repo = ElectronicFenceRepo(db)
        ef = repo.create(coords="[[0,0],[1,1]]")
        assert repo.delete(ef.id) is True

    def test_count_and_paginate(self, db):
        repo = ElectronicFenceRepo(db)
        for i in range(3):
            repo.create(coords=f"[[{i},{i}]]")
        assert repo.count() == 3
        items, total = repo.paginate(page=1, page_size=2)
        assert len(items) == 2
        assert total == 3

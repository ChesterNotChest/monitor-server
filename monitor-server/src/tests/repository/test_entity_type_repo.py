"""EntityTypeRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.entity_type_repo import EntityTypeRepo


class TestEntityTypeRepo:
    def test_create_and_get(self, db):
        repo = EntityTypeRepo(db)
        et = repo.create(name="person")
        assert et.id is not None
        assert repo.get(et.id).name == "person"

    def test_delete(self, db):
        repo = EntityTypeRepo(db)
        et = repo.create(name="car")
        assert repo.delete(et.id) is True

    def test_unique_name_violation(self, db):
        repo = EntityTypeRepo(db)
        repo.create(name="dog")
        with pytest.raises(IntegrityError):
            repo.create(name="dog")

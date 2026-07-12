"""SoundTypeRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.sound_type_repo import SoundTypeRepo


class TestSoundTypeRepo:
    def test_create_and_get(self, db):
        repo = SoundTypeRepo(db)
        st = repo.create(name="gunshot")
        assert st.id is not None
        assert repo.get(st.id).name == "gunshot"

    def test_delete(self, db):
        repo = SoundTypeRepo(db)
        st = repo.create(name="siren")
        assert repo.delete(st.id) is True

    def test_unique_name_violation(self, db):
        repo = SoundTypeRepo(db)
        repo.create(name="explosion")
        with pytest.raises(IntegrityError):
            repo.create(name="explosion")

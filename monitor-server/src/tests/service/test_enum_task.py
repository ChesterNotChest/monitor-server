"""enum_task 服务层冒烟测试。"""

import pytest
from src.service.enum_task import (
    EnumNameConflictError,
    create_entity,
    list_entities,
    update_entity,
    delete_entity,
    create_action,
    list_actions,
    update_action,
    delete_action,
    create_sound,
    list_sounds,
    update_sound,
    delete_sound,
)


class TestEntityType:
    def test_create_and_list(self, db):
        create_entity(db, "person")
        items = list_entities(db)
        assert len(items) >= 1
        assert items[0].name == "person"

    def test_create_duplicate(self, db):
        create_entity(db, "car")
        with pytest.raises(EnumNameConflictError):
            create_entity(db, "car")

    def test_update(self, db):
        e = create_entity(db, "dog")
        updated = update_entity(db, e.id, "cat")
        assert updated.name == "cat"

    def test_update_nonexistent(self, db):
        assert update_entity(db, 99999, "x") is None

    def test_delete(self, db):
        e = create_entity(db, "bird")
        assert delete_entity(db, e.id) is True
        assert delete_entity(db, e.id) is False


class TestActionType:
    def test_create_and_list(self, db):
        create_action(db, "walking")
        items = list_actions(db)
        assert len(items) >= 1

    def test_create_duplicate(self, db):
        create_action(db, "running")
        with pytest.raises(EnumNameConflictError):
            create_action(db, "running")

    def test_update(self, db):
        a = create_action(db, "falling")
        updated = update_action(db, a.id, "fighting")
        assert updated.name == "fighting"

    def test_delete(self, db):
        a = create_action(db, "climbing")
        assert delete_action(db, a.id) is True


class TestSoundType:
    def test_create_and_list(self, db):
        create_sound(db, "gunshot")
        items = list_sounds(db)
        assert len(items) >= 1

    def test_create_duplicate(self, db):
        create_sound(db, "scream")
        with pytest.raises(EnumNameConflictError):
            create_sound(db, "scream")

    def test_update(self, db):
        s = create_sound(db, "siren")
        updated = update_sound(db, s.id, "explosion")
        assert updated.name == "explosion"

    def test_delete(self, db):
        s = create_sound(db, "alarm")
        assert delete_sound(db, s.id) is True

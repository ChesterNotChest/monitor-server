"""exception_task 服务层冒烟测试。"""

from src.constants import SeverityLevel
from src.service.exception_task import (
    create_exception, list_exceptions, get_exception, update_exception, delete_exception,
    bind_entity, unbind_entity, bind_action, unbind_action, bind_sound, unbind_sound,
)
from src.service.enum_task import create_entity, create_action, create_sound
from src.service.alert_module.group import create_group


class TestExceptionDef:
    def _setup_group(self, db):
        return create_group(db, "测试告警组")

    def test_create_and_get(self, db):
        g = self._setup_group(db)
        exc = create_exception(db, name="创建测试", severity=SeverityLevel.CRITICAL, group_id=g.id)
        assert exc.id is not None
        found = get_exception(db, exc.id)
        assert found.severity == SeverityLevel.CRITICAL

    def test_list_all(self, db):
        g = self._setup_group(db)
        create_exception(db, name="列表测试", severity=SeverityLevel.WARNING, group_id=g.id)
        items, total = list_exceptions(db)
        assert total >= 1

    def test_list_by_severity(self, db):
        g = self._setup_group(db)
        create_exception(db, name="按严重度", severity=SeverityLevel.EMERGENCY, group_id=g.id)
        items, _ = list_exceptions(db, severity=SeverityLevel.EMERGENCY)
        assert all(e.severity == SeverityLevel.EMERGENCY for e in items)

    def test_update(self, db):
        g1 = self._setup_group(db)
        g2 = create_group(db, "另一组")
        exc = create_exception(db, name="更新测试", severity=SeverityLevel.INFO, group_id=g1.id)
        updated = update_exception(db, exc.id, severity=SeverityLevel.CRITICAL, group_id=g2.id)
        assert updated.severity == SeverityLevel.CRITICAL
        assert updated.group_id == g2.id

    def test_delete(self, db):
        g = self._setup_group(db)
        exc = create_exception(db, name="删除测试", severity=SeverityLevel.WARNING, group_id=g.id)
        assert delete_exception(db, exc.id) is True
        assert get_exception(db, exc.id) is None


class TestM2MBinding:
    def _setup(self, db):
        g = create_group(db, "绑定测试")
        exc = create_exception(db, name="绑定异常", severity=SeverityLevel.CRITICAL, group_id=g.id)
        return exc

    def test_bind_entity(self, db):
        exc = self._setup(db)
        ent = create_entity(db, "person")
        result = bind_entity(db, exc.id, ent.id)
        assert len(result) == 1
        result = bind_entity(db, exc.id, ent.id)
        assert len(result) == 1

    def test_unbind_entity(self, db):
        exc = self._setup(db)
        ent = create_entity(db, "car")
        bind_entity(db, exc.id, ent.id)
        assert unbind_entity(db, exc.id, ent.id) is True

    def test_bind_action(self, db):
        exc = self._setup(db)
        act = create_action(db, "running")
        result = bind_action(db, exc.id, act.id)
        assert len(result) == 1

    def test_unbind_action(self, db):
        exc = self._setup(db)
        act = create_action(db, "walking")
        bind_action(db, exc.id, act.id)
        assert unbind_action(db, exc.id, act.id) is True

    def test_bind_sound(self, db):
        exc = self._setup(db)
        snd = create_sound(db, "gunshot")
        result = bind_sound(db, exc.id, snd.id)
        assert len(result) == 1

    def test_unbind_sound(self, db):
        exc = self._setup(db)
        snd = create_sound(db, "scream")
        bind_sound(db, exc.id, snd.id)
        assert unbind_sound(db, exc.id, snd.id) is True

    def test_bind_nonexistent_exception(self, db):
        ent = create_entity(db, "dog")
        assert bind_entity(db, 99999, ent.id) is None

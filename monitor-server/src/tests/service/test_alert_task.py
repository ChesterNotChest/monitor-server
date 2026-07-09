"""alert_task 服务层冒烟测试。"""

import pytest
from src.service.alert_task import (
    create_response,
    list_responses,
    update_response,
    delete_response,
    create_group,
    list_groups,
    get_group,
    update_group,
    delete_group,
    bind_response,
    unbind_response,
    get_group_responses,
)
from src.service.enum_task import EnumNameConflictError


class TestResponseAction:
    def test_create_and_list(self, db):
        create_response(db, "trigger_recording")
        items = list_responses(db)
        assert len(items) >= 1

    def test_create_duplicate(self, db):
        create_response(db, "send_notification")
        with pytest.raises(EnumNameConflictError):
            create_response(db, "send_notification")

    def test_update(self, db):
        r = create_response(db, "activate_alarm")
        updated = update_response(db, r.id, "call_api")
        assert updated.name == "call_api"

    def test_delete(self, db):
        r = create_response(db, "send_email")
        assert delete_response(db, r.id) is True


class TestAlertGroup:
    def test_create_and_list(self, db):
        create_group(db, "高优先级")
        items, total = list_groups(db)
        assert total >= 1

    def test_create_duplicate(self, db):
        create_group(db, "中优先级")
        with pytest.raises(EnumNameConflictError):
            create_group(db, "中优先级")

    def test_get(self, db):
        g = create_group(db, "低优先级")
        found = get_group(db, g.id)
        assert found.name == "低优先级"

    def test_update(self, db):
        g = create_group(db, "测试分组")
        updated = update_group(db, g.id, "紧急优先级")
        assert updated.name == "紧急优先级"

    def test_delete(self, db):
        g = create_group(db, "待删除")
        assert delete_group(db, g.id) is True


class TestBinding:
    def test_bind_and_unbind(self, db):
        g = create_group(db, "绑定测试组")
        r1 = create_response(db, "notify_1")
        r2 = create_response(db, "notify_2")

        # bind
        result = bind_response(db, g.id, r1.id)
        assert result is not None
        assert len(result) == 1

        # bind another
        result = bind_response(db, g.id, r2.id)
        assert len(result) == 2

        # idempotent bind
        result = bind_response(db, g.id, r1.id)
        assert len(result) == 2

        # unbind
        assert unbind_response(db, g.id, r1.id) is True
        responses = get_group_responses(db, g.id)
        assert len(responses) == 1

        # idempotent unbind — returns True (group exists)
        assert unbind_response(db, g.id, r1.id) is True

    def test_bind_nonexistent_group(self, db):
        r = create_response(db, "orphan_action")
        result = bind_response(db, 99999, r.id)
        assert result is None

    def test_get_responses_nonexistent(self, db):
        assert get_group_responses(db, 99999) is None

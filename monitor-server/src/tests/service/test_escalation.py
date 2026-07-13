"""逐级上报引擎测试。"""
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.service.alert_module.escalation import (
    ESCALATION_ROLES,
    STATUS_CREATED,
    STATUS_ACKNOWLEDGED,
    STATUS_ESCALATED,
    STATUS_HANDLED,
    STATUS_FALSE_ALARM,
    _get_escalation_chain,
    _determine_responders,
    _generate_ack_token,
    verify_ack_token,
    recover_timers,
)


class TestEscalationChain:
    """上级链查询测试。"""

    def test_chain_from_security_guard(self):
        chain = _get_escalation_chain("security_guard")
        assert chain == ["security_guard", "manager"]

    def test_chain_from_manager(self):
        chain = _get_escalation_chain("manager")
        assert chain == ["manager"]

    def test_chain_unknown_role_falls_back_to_manager(self):
        chain = _get_escalation_chain("unknown")
        assert chain == ["manager"]


class TestAckToken:
    """确认 token 生成与验证测试。"""

    def test_generate_and_verify_valid_token(self):
        token = _generate_ack_token(42)
        assert verify_ack_token(42, token) is True

    def test_wrong_alert_id(self):
        token = _generate_ack_token(42)
        assert verify_ack_token(99, token) is False

    def test_expired_token(self, monkeypatch):
        monkeypatch.setattr("src.service.alert_module.escalation.settings.ESCALATION_TIMEOUT_SECONDS", -1)
        token = _generate_ack_token(1)
        assert verify_ack_token(1, token) is False

    def test_invalid_token(self):
        assert verify_ack_token(1, "not.a.valid.token") is False


class TestStatusConstants:
    """状态常量测试。"""

    def test_all_statuses_defined(self):
        assert STATUS_CREATED == "created"
        assert STATUS_ACKNOWLEDGED == "acknowledged"
        assert STATUS_ESCALATED == "escalated"
        assert STATUS_HANDLED == "handled"
        assert STATUS_FALSE_ALARM == "false_alarm"

    def test_escalation_roles_order(self):
        # security_guard → manager, no further
        assert ESCALATION_ROLES[0] == "security_guard"
        assert ESCALATION_ROLES[1] == "manager"
        assert len(ESCALATION_ROLES) == 2


@pytest.mark.asyncio
async def test_recover_timers_snapshots_event_before_session_close(monkeypatch):
    from src.service.alert_module import escalation

    escalation._timers.clear()
    detached = {"closed": False}

    class Severity:
        name = "CRITICAL"

    class ExceptionDef:
        id = 7
        group_id = 8
        name = "critical-alert"
        severity = Severity()

    class Event:
        id = 9
        view_id = 10
        exception_id = 7
        status = STATUS_CREATED
        timestamp = datetime.now(timezone.utc)

        @property
        def exception(self):
            if detached["closed"]:
                raise RuntimeError("detached relationship access")
            return ExceptionDef()

    class ScalarResult:
        def all(self):
            return [Event()]

    class Session:
        def scalars(self, _stmt):
            return ScalarResult()

        def close(self):
            detached["closed"] = True

    created = []

    def fake_create_task(coro, name=None):
        created.append((coro, name))
        coro.close()
        return SimpleNamespace(cancel=lambda: None)

    monkeypatch.setattr("src.service.alert_module.escalation.SessionLocal", lambda: Session())
    monkeypatch.setattr(
        "src.service.alert_module.escalation._find_users_by_role",
        lambda role: [SimpleNamespace(username="guard", dingtalk_mobile="13800000000")],
    )
    monkeypatch.setattr("src.service.alert_module.escalation.asyncio.create_task", fake_create_task)

    await recover_timers()

    assert len(created) == 1
    assert created[0][1] == "esc-timer-9"
    escalation._timers.clear()

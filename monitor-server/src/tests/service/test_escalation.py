"""逐级上报引擎测试。"""
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

"""逐级上报引擎 —— 告警通知 → 超时上报 → 确认取消。

设计：
  - 高危告警（CRITICAL / EMERGENCY）→ @安全员(security_guard)
  - X 秒未确认 → @负责人(manager)
  - 负责人也未确认 → 继续循环 @负责人
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import select

from src.config import settings
from src.constants import SeverityLevel
from src.extensions import SessionLocal

logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────

STATUS_CREATED = "created"
STATUS_ACKNOWLEDGED = "acknowledged"
STATUS_ESCALATED = "escalated"
STATUS_HANDLED = "handled"
STATUS_FALSE_ALARM = "false_alarm"

ESCALATION_ROLES = ["security_guard", "manager"]  # 上报链角色顺序

_timers: dict[int, asyncio.Task] = {}  # alert_id → timer task
_acked: set[int] = set()               # 已确认的 alert_id（跨协程通信）


def _event_snapshot(event):
    """Copy ORM event fields needed by async timers before its Session closes."""
    exc = getattr(event, "exception", None)
    exc_snapshot = None
    if exc is not None:
        severity = getattr(exc, "severity", None)
        exc_snapshot = SimpleNamespace(
            id=getattr(exc, "id", None),
            group_id=getattr(exc, "group_id", None),
            name=getattr(exc, "name", None),
            severity=SimpleNamespace(name=getattr(severity, "name", str(severity))),
        )

    return SimpleNamespace(
        id=event.id,
        view_id=event.view_id,
        exception_id=getattr(event, "exception_id", None),
        status=getattr(event, "status", None),
        timestamp=getattr(event, "timestamp", None),
        exception=exc_snapshot,
    )


# ── 责任人查找 ───────────────────────────────────

def _find_users_by_role(role: str) -> list:
    """按 role 查找所有活跃用户（包含未绑手机号的）。"""
    from src.models.user import User
    db = SessionLocal()
    try:
        return list(db.scalars(
            select(User).where(
                User.role == role,
                User.is_active == True,
            )
        ).all())
    finally:
        db.close()


def _get_escalation_chain(current_role: str) -> list[str]:
    """返回从 current_role 开始的剩余上报角色列表。"""
    try:
        idx = ESCALATION_ROLES.index(current_role)
    except ValueError:
        return ["manager"]
    return ESCALATION_ROLES[idx:]  # 包含当前角色在内的剩余链


def _determine_responders(alert_group, event) -> tuple[list, str]:
    """确定第一级响应人。返回 (users, role)。"""
    db = SessionLocal()
    try:
        # 1. AlertGroup.default_assignee
        if alert_group and alert_group.default_assignee_id:
            from src.models.user import User
            assignee = db.get(User, alert_group.default_assignee_id)
            if assignee and assignee.is_active and assignee.dingtalk_mobile:
                return [assignee], assignee.role or "security_guard"

        # 2. 按 role 查找安全员
        guards = _find_users_by_role("security_guard")
        if guards:
            return guards, "security_guard"

        # 3. 安全员都没有就找负责人
        managers = _find_users_by_role("manager")
        if managers:
            return managers, "manager"

        return [], "security_guard"
    finally:
        db.close()


# ── 日志 ─────────────────────────────────────────

def _write_log(summary: str, severity: int, event_id: int, view_id: int | None = None) -> None:
    """写一条系统日志。"""
    from src.models.log_entry import LogEntry
    db = SessionLocal()
    try:
        log = LogEntry(
            log_type=2,  # 告警类型
            severity=severity,
            summary=summary,
            event_id=event_id,
            view_id=view_id,
        )
        db.add(log)
        db.commit()
    except Exception:
        logger.exception("Failed to write log: %s", summary)
    finally:
        db.close()


# ── 消息模板 ─────────────────────────────────────

_SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "EMERGENCY": "🚨",
    "WARNING": "⚠️",
    "INFO": "ℹ️",
}


def _build_alert_message(event, users: list, view_name: str, ack_url: str) -> tuple[str, str]:
    """构建告警通知消息。返回 (title, markdown_text)。"""
    exc = event.exception if hasattr(event, "exception") else None
    sev_name = exc.severity.name if exc and hasattr(exc, "severity") else "UNKNOWN"
    exc_name = exc.name if exc else "未知"
    emoji = _SEVERITY_EMOJI.get(sev_name, "📢")
    names = ", ".join(
        u.username if u.dingtalk_mobile else f"{u.username}(未绑定手机号)"
        for u in users
    )
    mobiles_with_phone = [u for u in users if u.dingtalk_mobile]
    mobiles = "@" + " @".join(u.dingtalk_mobile for u in mobiles_with_phone) if mobiles_with_phone else ""

    title = f"{emoji} 告警通知 - {sev_name}"
    text = (
        f"## {emoji} 告警通知\n\n"
        f"**级别**: {sev_name}\n"
        f"**摄像头**: {view_name}\n"
        f"**检测到**: {exc_name}\n"
        f"**时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"---\n\n"
        f"**责任人**: {names} {mobiles}\n"
        f"请在 {settings.ESCALATION_TIMEOUT_SECONDS} 秒内确认处理\n\n"
        f"[点击确认处理]({ack_url})"
    )
    return title, text


def _build_escalation_message(event, users: list, from_role: str, view_name: str, ack_url: str) -> tuple[str, str]:
    """构建升级通知消息。"""
    exc = event.exception if hasattr(event, "exception") else None
    sev_name = exc.severity.name if exc and hasattr(exc, "severity") else "UNKNOWN"
    names = ", ".join(
        u.username if u.dingtalk_mobile else f"{u.username}(未绑定手机号)"
        for u in users
    )

    title = f"⚠️ 告警未响应 - 已上报"
    text = (
        f"## ⚠️ 告警未响应\n\n"
        f"**原告警**: {sev_name} - {view_name}\n"
        f"**{from_role}** 未在 {settings.ESCALATION_TIMEOUT_SECONDS} 秒内响应\n"
        f"**已上报至**: {names}\n\n"
        f"---\n\n"
        f"请在 {settings.ESCALATION_TIMEOUT_SECONDS} 秒内确认处理\n\n"
        f"[点击确认处理]({ack_url})"
    )
    return title, text


def _build_ack_message(username: str, event_id: int) -> str:
    """构建确认消息。"""
    return f"✅ {username} 已确认处理告警 #{event_id}"


# ── 上报引擎 ─────────────────────────────────────

async def start_escalation_from_id(event_id: int, view_id: int, view_name: str,
                                    group_id: int | None) -> None:
    """从 ID 启动逐级上报（用于 sync endpoint 避免 DetachedInstanceError）。"""
    db = SessionLocal()
    try:
        from src.models.situation_event import SituationEvent
        from src.models.alert_group import AlertGroup
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select as _sel

        event = db.scalar(
            _sel(SituationEvent)
            .where(SituationEvent.id == event_id)
            .options(selectinload(SituationEvent.exception))
        )
        if not event:
            return

        alert_group = None
        if group_id:
            alert_group = db.scalar(
                _sel(AlertGroup)
                .where(AlertGroup.id == group_id)
                .options(selectinload(AlertGroup.responses))
            )

        await start_escalation(_event_snapshot(event), alert_group, view_name)
    finally:
        db.close()


async def start_escalation(event, alert_group, view_name: str) -> None:
    """启动逐级上报流程。"""
    event = _event_snapshot(event) if not isinstance(event, SimpleNamespace) else event
    alert_id = event.id
    responders, role = _determine_responders(alert_group, event)

    if not responders:
        logger.warning("No responders found for alert %d", alert_id)
        return

    # 发送第一级通知
    ack_url = _build_ack_url(alert_id)
    title, text = _build_alert_message(event, responders, view_name, ack_url)
    mobiles = [u.dingtalk_mobile for u in responders if u.dingtalk_mobile]

    await _send_notification(event, title, text, mobiles)

    names = ", ".join(u.username for u in responders)
    _write_log(f"告警 #{alert_id} 已通过钉钉通知{role}: {names}", 1, alert_id, event.view_id)

    # 启动计时器
    chain = _get_escalation_chain(role)
    task = asyncio.create_task(
        _escalation_timer(event, chain, 0, view_name, alert_group),
        name=f"esc-timer-{alert_id}",
    )
    _timers[alert_id] = task


async def acknowledge(alert_id: int, user) -> bool:
    """确认告警，取消上报计时器。"""
    if alert_id in _acked:
        return True  # 已确认

    _acked.add(alert_id)

    # 取消计时器
    task = _timers.pop(alert_id, None)
    if task:
        task.cancel()

    # 更新状态
    db = SessionLocal()
    try:
        from src.models.situation_event import SituationEvent
        event = db.get(SituationEvent, alert_id)
        if event:
            event.status = STATUS_ACKNOWLEDGED
            db.commit()

            # 写确认日志
            _write_log(f"告警 #{alert_id} 已被 {user.username} 确认处理", 1, alert_id, event.view_id)

            # 发确认消息
            msg = _build_ack_message(user.username, alert_id)
            await _send_simple_notification(msg, [])
            return True
    except Exception:
        logger.exception("acknowledge failed for alert %d", alert_id)
        db.rollback()
        return False
    finally:
        db.close()
    return False


async def stop_escalation(alert_id: int) -> None:
    """停止上报（View 删除时调用）。"""
    _acked.discard(alert_id)
    task = _timers.pop(alert_id, None)
    if task:
        task.cancel()


# ── 内部 ─────────────────────────────────────────

async def _escalation_timer(event, chain: list[str], level: int, view_name: str,
                            alert_group) -> None:
    """计时协程：超时后上报到下一级。"""
    alert_id = event.id
    await asyncio.sleep(settings.ESCALATION_TIMEOUT_SECONDS)

    if alert_id in _acked:
        return  # 已确认，取消上报

    # 确定下一级：优先 supervisor 链，其次 role 广播
    next_level = level + 1
    if next_level >= len(chain):
        # 已在链末端（manager），循环通知
        users = _find_users_by_role(chain[-1])
        role = chain[-1]
    else:
        role = chain[next_level]
        # 先看当前级别用户的 supervisor 链
        from src.models.user import User as _User
        current_users = _find_users_by_role(chain[level])
        supervisors = []
        for u in current_users:
            if u.supervisor_id:
                db2 = SessionLocal()
                try:
                    sup = db2.get(_User, u.supervisor_id)
                    if sup and sup.is_active and sup.dingtalk_mobile:
                        supervisors.append(sup)
                finally:
                    db2.close()
        if supervisors:
            users = supervisors
        else:
            users = _find_users_by_role(role)

    if not users:
        logger.warning("No users for role %s, alert %d", role, alert_id)
        return

    # 更新状态
    db = SessionLocal()
    try:
        from src.models.situation_event import SituationEvent
        ev = db.get(SituationEvent, alert_id)
        if ev:
            ev.status = STATUS_ESCALATED
            db.commit()
    finally:
        db.close()

    # 写升级日志
    from_role = chain[level] if level < len(chain) else chain[-1]
    from src.models.escalation_log import EscalationLog
    db = SessionLocal()
    try:
        log_entry = EscalationLog(
            alert_id=alert_id,
            level=next_level,
            from_role=from_role,
            to_role=role,
        )
        db.add(log_entry)
        db.commit()
    finally:
        db.close()

    # 发升级通知
    ack_url = _build_ack_url(alert_id)
    title, text = _build_escalation_message(event, users, from_role, view_name, ack_url)
    mobiles = [u.dingtalk_mobile for u in users if u.dingtalk_mobile]

    await _send_notification(event, title, text, mobiles)

    names = ", ".join(u.username for u in users)
    if next_level >= len(chain):
        _write_log(f"告警 #{alert_id} 负责人仍未响应，再次通知", 2, alert_id, event.view_id)
    else:
        _write_log(f"告警 #{alert_id} {from_role}未响应，已上报至{role}", 2, alert_id, event.view_id)

    # 继续计时（链末端循环）
    next_chain = chain[next_level:] if next_level < len(chain) else chain[-1:]
    _timers[alert_id] = asyncio.create_task(
        _escalation_timer(event, chain, next_level if next_level < len(chain) else level + 1,
                          view_name, alert_group),
        name=f"esc-timer-{alert_id}",
    )


async def _send_notification(event, title: str, text: str, at_mobiles: list[str]) -> None:
    """通过通知分发器发送消息。"""
    try:
        from .channel import NotificationPayload, dispatch

        exc = event.exception if hasattr(event, "exception") else None
        responses: list = []
        db = SessionLocal()
        try:
            if exc and exc.group_id:
                from src.models.alert_group import AlertGroup
                from sqlalchemy.orm import selectinload
                from sqlalchemy import select as _select
                alert_group = db.scalar(
                    _select(AlertGroup)
                    .where(AlertGroup.id == exc.group_id)
                    .options(selectinload(AlertGroup.responses))
                )
                if alert_group:
                    responses = list(alert_group.responses)
        finally:
            db.close()

        payload = NotificationPayload(
            title=title,
            text=text,
            at_mobiles=at_mobiles,
            alert_id=event.id,
            severity=exc.severity.name if exc else None,
            exception_name=exc.name if exc else None,
        )

        await dispatch(payload, responses)
    except Exception:
        logger.exception("Failed to send notification for alert %d", event.id)


async def _send_simple_notification(text: str, at_mobiles: list[str]) -> None:
    """发送简单通知（确认消息等），绕过 ResponseAction 直接调 webhook。"""
    try:
        from src.config import settings
        from .channel import NotificationPayload
        from .channel.dingtalk_webhook import DingTalkWebhookChannel

        import os
        webhook_url = settings.DINGTALK_WEBHOOK_URL or os.getenv("DINGTALK_WEBHOOK", "")
        if not webhook_url:
            return

        channel = DingTalkWebhookChannel()
        payload = NotificationPayload(title="告警更新", text=text, at_mobiles=at_mobiles)
        await channel.send(payload, {"webhook_url": webhook_url})
    except Exception:
        pass


def _build_ack_url(alert_id: int) -> str:
    """构建确认链接（含短期 token）。"""
    from src.config import settings
    host = settings.HOST if settings.HOST != "0.0.0.0" else "127.0.0.1"
    token = _generate_ack_token(alert_id)
    return f"http://{host}:{settings.PORT}/api/v1/alerts/{alert_id}/ack?token={token}"


# ── ACK Token ───────────────────────────────────

def _generate_ack_token(alert_id: int) -> str:
    """生成短期确认 token（JWT，过期时间 = escalation_timeout）。"""
    from jose import jwt as _jwt
    import time as _time
    payload = {
        "alert_id": alert_id,
        "action": "acknowledge",
        "exp": _time.time() + settings.ESCALATION_TIMEOUT_SECONDS,
    }
    return _jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_ack_token(alert_id: int, token: str) -> bool:
    """验证确认 token。"""
    from jose import jwt as _jwt
    try:
        payload = _jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("alert_id") == alert_id and payload.get("action") == "acknowledge"
    except Exception:
        return False


# ── 重启恢复 ─────────────────────────────────────

async def recover_timers() -> None:
    """Server 启动时扫描未确认告警，重建计时器。"""
    db = SessionLocal()
    try:
        from src.models.situation_event import SituationEvent
        from sqlalchemy.orm import selectinload
        events = [
            _event_snapshot(ev)
            for ev in db.scalars(
                select(SituationEvent)
                .where(SituationEvent.status.in_([STATUS_CREATED, STATUS_ESCALATED]))
                .options(selectinload(SituationEvent.exception))
            ).all()
        ]
    finally:
        db.close()

    for ev in events:
        alert_id = ev.id
        if alert_id in _acked or alert_id in _timers:
            continue

        ev_view_id = ev.view_id
        ev_status = ev.status
        ev_timestamp = ev.timestamp

        # 确定当前上报角色级别
        if ev_status == STATUS_CREATED:
            level = 0
        else:
            db2 = SessionLocal()
            try:
                from src.models.escalation_log import EscalationLog
                last = db2.scalar(
                    select(EscalationLog).where(
                        EscalationLog.alert_id == alert_id
                    ).order_by(EscalationLog.escalated_at.desc()).limit(1)
                )
                level = last.level if last else 1
            finally:
                db2.close()

        elapsed = (datetime.now(timezone.utc) - ev_timestamp.replace(tzinfo=timezone.utc)).total_seconds()

        if level < len(ESCALATION_ROLES):
            role = ESCALATION_ROLES[level]
        else:
            role = ESCALATION_ROLES[-1]

        users = _find_users_by_role(role)
        if not users:
            continue

        view_name = f"View {ev_view_id}"
        chain = _get_escalation_chain(role)
        _timers[alert_id] = asyncio.create_task(
            _escalation_timer(ev, chain, level, view_name, None),
            name=f"esc-timer-{alert_id}",
        )
        logger.info("Recovered escalation timer for alert %d (level=%d)", alert_id, level)

    logger.info("Escalation recovery complete: %d timers rebuilt", len(_timers))

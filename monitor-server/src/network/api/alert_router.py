"""告警 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.alert_schema import AlertListResponse, AlertResponse
from src.schema.http.common import OkResponse
from src.service import alert_task

router = APIRouter(prefix="/alerts", tags=["告警"])


@router.post("/debug-test", response_model=OkResponse)
async def debug_trigger_alert(db: Session = Depends(get_db)):
    """DEBUG: 手动创建一个测试告警并触发钉钉通知。

    用数据库中第一条 CRITICAL 或 EMERGENCY 异常规则创建告警，
    测试完整的通知 → 上报链路。
    """
    from sqlalchemy import select
    from src.constants import SeverityLevel
    from src.models.exception import ExceptionDef
    from src.models.monitor_view import MonitorView

    exc = db.scalar(
        select(ExceptionDef).where(
            ExceptionDef.severity.in_([SeverityLevel.CRITICAL, SeverityLevel.EMERGENCY])
        ).limit(1)
    )
    if exc is None:
        raise HTTPException(400, "数据库中没有 CRITICAL/EMERGENCY 异常规则，请先运行 seed_data")

    view = db.scalar(select(MonitorView).limit(1))
    if view is None:
        raise HTTPException(400, "数据库中没有任何 View，请先创建视图")

    # 创建告警
    from src.repository.situation_event_repo import SituationEventRepo
    from src.service.alert_module.escalation import STATUS_CREATED
    event = SituationEventRepo(db).create(view_id=view.id, exception_id=exc.id)
    event.status = STATUS_CREATED
    db.commit()
    db.refresh(event)

    event_id = event.id
    event_view_id = event.view_id
    view_name = view.name or f"View {view.id}"
    group_id = exc.group_id

    # eager load
    from src.models.alert_group import AlertGroup
    from sqlalchemy.orm import selectinload
    resp_channels: list[str] = []
    if group_id:
        ag = db.scalar(
            select(AlertGroup)
            .where(AlertGroup.id == group_id)
            .options(selectinload(AlertGroup.responses))
        )
        if ag and ag.responses:
            resp_channels = [r.channel for r in ag.responses if r.channel]

    # 触发通知（async endpoint 里直接用 create_task，计时器不会被销毁）
    if "dingtalk_webhook" in resp_channels:
        from src.service.alert_module import escalation as _esc
        import asyncio
        asyncio.create_task(
            _esc.start_escalation_from_id(event_id, event_view_id, view_name, group_id),
            name=f"debug-escalation-{event_id}",
        )

    return OkResponse()


@router.get("", response_model=AlertListResponse)
def list_alerts(
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    _user=Depends(require_permission("alert:list")),
):
    """告警列表（分页）。"""
    return alert_task.list_alerts(db, page=page, page_size=page_size)


@router.get(
    "/{alert_id}/ack",
    response_model=OkResponse,
    responses={404: {"description": "告警不存在"}, 403: {"description": "Token 无效或过期"}},
)
def verify_ack(
    alert_id: int,
    token: str = Query(..., description="确认 token"),
    db: Session = Depends(get_db),
):
    """钉钉消息中的确认链接 —— 验证 token 并执行确认。"""
    from src.service.alert_module.escalation import verify_ack_token
    if not verify_ack_token(alert_id, token):
        raise HTTPException(status_code=403, detail="Token 无效或已过期")
    # 直接执行确认，取消上报计时器
    alert_task.acknowledge_alert(db, alert_id, user_id=1)  # user_id=1 作为系统自动确认
    return OkResponse()


@router.put(
    "/{alert_id}/acknowledge",
    response_model=OkResponse,
    responses={404: {"description": "告警不存在"}},
)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("alert:handle")),
):
    """确认告警 —— 标记为已知悉，取消逐级上报计时器。

    **权限**: alert:handle
    """
    if not alert_task.acknowledge_alert(db, alert_id, user.id):
        raise HTTPException(status_code=404, detail="告警不存在或用户不存在")
    return OkResponse()


@router.put(
    "/{alert_id}/handle",
    response_model=OkResponse,
    responses={404: {"description": "告警不存在"}},
)
def mark_handled(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("alert:handle")),
):
    """标记告警为已处理。

    **权限**: alert:handle
    """
    if not alert_task.mark_handled(db, alert_id, user.id):
        raise HTTPException(status_code=404, detail="告警不存在")
    return OkResponse()


@router.put(
    "/{alert_id}/false-alarm",
    response_model=OkResponse,
    responses={404: {"description": "告警不存在"}},
)
def mark_false_alarm(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("alert:handle")),
):
    """标记告警为误报。

    **权限**: alert:handle
    """
    if not alert_task.mark_false_alarm(db, alert_id, user.id):
        raise HTTPException(status_code=404, detail="告警不存在")
    return OkResponse()

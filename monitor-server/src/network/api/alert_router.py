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
@router.post("/debug-test/", response_model=OkResponse, include_in_schema=False)
async def debug_trigger_alert(db: Session = Depends(get_db)):
    """DEBUG: 发送一条钉钉测试消息，不依赖已有 View 或高危异常规则。"""
    import json
    from sqlalchemy import select

    from src.models.response_action import ResponseAction
    from src.models.user import User
    from src.service.alert_module.channel import NotificationPayload
    from src.service.alert_module.channel.dingtalk_webhook import DingTalkWebhookChannel

    actions = list(db.scalars(
        select(ResponseAction).where(ResponseAction.channel == "dingtalk_webhook")
    ).all())
    if not actions:
        raise HTTPException(400, "没有配置 dingtalk_webhook 响应动作")

    at_mobiles = list(db.scalars(
        select(User.dingtalk_mobile).where(
            User.is_active == True,
            User.dingtalk_mobile.is_not(None),
            User.dingtalk_mobile != "",
        )
    ).all())

    payload = NotificationPayload(
        title="告警通知 - DEBUG",
        text=(
            "## 告警通知 - DEBUG\n\n"
            "这是一条 monitor-server 钉钉连通性测试消息。\n\n"
            "如果能看到此消息，说明 webhook 与响应动作配置可用。"
        ),
        at_mobiles=at_mobiles,
        alert_id=0,
        severity="DEBUG",
        exception_name="debug-test",
    )

    channel = DingTalkWebhookChannel()
    saw_valid_config = False
    for action in actions:
        config = {}
        if action.config_json:
            try:
                config = json.loads(action.config_json)
            except json.JSONDecodeError:
                continue
        if not channel.validate_config(config):
            continue
        saw_valid_config = True
        if await channel.send(payload, config):
            return OkResponse()

    if not saw_valid_config:
        raise HTTPException(400, "钉钉 webhook 未配置")
    raise HTTPException(502, "钉钉消息发送失败，请查看后端日志中的 DingTalk errcode")



@router.get("/", response_model=AlertListResponse)
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
    "/{alert_id}/handle/",
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
    db.commit()
    return OkResponse()


@router.put(
    "/{alert_id}/false-alarm/",
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
    db.commit()
    return OkResponse()

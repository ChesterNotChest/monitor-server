"""API 路由汇总 —— 聚合所有子 Router，供 app.py 一次性注册。"""

from .alert_group_router import router as alert_group_router
from .alert_router import router as alert_router
from .auth_router import router as auth_router
from .dashboard_router import router as dashboard_router
from .detection_router import entity_router, action_router, sound_router
from .device_router import router as device_router
from .event import router as event_router, stats_router
from .exception_router import router as exception_router
from .fence_router import router as fence_router
from .log_router import router as log_router
from .node_router import router as node_router
from .replay import router as replay_router
from .report_router import router as report_router
from .user_router import router as user_router
from .view_router import router as view_router

routers = [
    auth_router,
    alert_router,
    alert_group_router,
    dashboard_router,
    device_router,
    entity_router,
    action_router,
    sound_router,
    event_router,
    stats_router,
    exception_router,
    fence_router,
    log_router,
    node_router,
    replay_router,
    report_router,
    user_router,
    view_router,
]

__all__ = ["routers"]

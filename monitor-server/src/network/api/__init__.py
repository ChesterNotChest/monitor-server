"""API 路由汇总 —— 聚合所有子 Router，供 app.py 一次性注册。"""

from .node_router import router as node_router
from .view_router import router as view_router
from .enum_types import entity_router, action_router, sound_router
from .alert import response_router, group_router
from .exception import router as exception_router
from .event import router as event_router, stats_router
from .user import router as user_router
from .log import router as log_router
from .replay import router as replay_router

routers = [
    node_router,
    view_router,
    entity_router,
    action_router,
    sound_router,
    response_router,
    group_router,
    exception_router,
    event_router,
    stats_router,
    user_router,
    log_router,
    replay_router,
]

__all__ = [
    "routers",
    "node_router",
    "view_router",
    "entity_router",
    "action_router",
    "sound_router",
    "response_router",
    "group_router",
    "exception_router",
    "event_router",
    "stats_router",
]

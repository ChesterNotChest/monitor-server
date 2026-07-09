"""API 路由汇总 —— 聚合所有子 Router，供 app.py 一次性注册。"""

from .node_router import router as node_router
from .view_router import router as view_router

routers = [node_router, view_router]

__all__ = ["routers", "node_router", "view_router"]

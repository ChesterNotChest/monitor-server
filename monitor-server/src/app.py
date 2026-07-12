"""
FastAPI 应用入口 —— 创建 app 实例、注册中间件、引入路由。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.constants import API_PREFIX
from src.service.view_module.ffmpeg_manager import cleanup_all

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS —— 生产环境请收紧 origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查端点。"""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.on_event("startup")
async def print_urls():
    """启动时输出可点击的访问地址。"""
    host = settings.HOST if settings.HOST != "0.0.0.0" else "localhost"
    port = settings.PORT
    print(f"\n{'='*60}")
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"{'='*60}")
    print(f"  API Docs:     http://{host}:{port}/docs")
    print(f"  ReDoc:        http://{host}:{port}/redoc")
    print(f"  Health Check: http://{host}:{port}/health")
    print(f"{'='*60}\n")

    import logging
    from src.extensions import engine, Base
    from src.seed import seed_admin

    # 确保数据库表存在（非测试环境可能未建表）
    Base.metadata.create_all(bind=engine)

    try:
        seed_admin()
    except Exception as e:
        logging.getLogger(__name__).warning("seed_admin failed: %s", e)

    # Debug FLV 测试数据链路
    if settings.DEBUG_FLV_TRANSMIT:
        from src.debug_data import start_debug_data
        start_debug_data()


@app.on_event("shutdown")
async def shutdown_cleanup():
    """服务关闭时终止所有 FFmpeg 子进程。"""
    cleanup_all()


# ---- 注册子路由 ----
from src.network.api.named_person import router as named_person_router

app.include_router(named_person_router)

# ---- 注册 API 路由 ----
from src.network.api import routers as api_routers
for router in api_routers:
    app.include_router(router, prefix=API_PREFIX)

# ---- 注册 Node WebSocket 端点 ----
from src.network.wss.node_handler import node_websocket_endpoint

app.add_api_websocket_route("/ws", node_websocket_endpoint)
app.add_api_websocket_route(f"{API_PREFIX}/ws", node_websocket_endpoint)

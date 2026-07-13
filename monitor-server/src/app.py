"""
FastAPI 应用入口 —— 创建 app 实例、注册中间件、引入路由。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

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

# 静态文件：命名人物头像
_face_dir = os.path.abspath(settings.FACE_IMAGE_DIR)
os.makedirs(_face_dir, exist_ok=True)
app.mount("/face_images", StaticFiles(directory=_face_dir), name="face_images")


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
    from src.seed import seed_admin, seed_fence_events

    # 确保数据库表存在（非测试环境可能未建表）
    Base.metadata.create_all(bind=engine)

    try:
        seed_admin()
    except Exception as e:
        logging.getLogger(__name__).warning("seed_admin failed: %s", e)

    try:
        seed_fence_events()
    except Exception as e:
        logging.getLogger(__name__).warning("seed_fence_events failed: %s", e)

    # 恢复已有 View 的 AI 管线（Server 重启后自动续接）
    from src.extensions import SessionLocal
    from src.repository.monitor_view_repo import MonitorViewRepo
    _db = SessionLocal()
    try:
        _views = MonitorViewRepo(_db).all(limit=1000)
        _logger = logging.getLogger(__name__)
        _logger.info("[Recovery] DB has %d view(s)", len(_views))
        if _views:
            import asyncio as _asyncio
            from src.service.vision_task import start_pipeline as _start_pipeline, _active_pipelines
            _recovered = 0
            _skipped = 0
            for _v in _views:
                _vid = _v.video_id
                _aid = _v.audio_id
                _vname = _v.video_device.name
                _aname = _v.audio_device.name
                _view_id = _v.id
                if _view_id in _active_pipelines:
                    _logger.info("[Recovery] View %d: SKIP (already active)", _view_id)
                    _skipped += 1
                    continue
                def _launch(vid=_view_id, vname=_vname, aname=_aname):
                    async def _forever():
                        await _start_pipeline(vid, _vid, vname, _aid, aname)
                        while True:
                            await _asyncio.sleep(3600)
                    _asyncio.create_task(_forever())
                _launch()
                _recovered += 1
            _logger.info("[Recovery] recovered=%d skipped=%d total=%d",
                        _recovered, _skipped, len(_views))
    except Exception as e:
        logging.getLogger(__name__).warning("[Recovery] skipped: %s", e)
    finally:
        _db.close()


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

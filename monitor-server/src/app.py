"""
FastAPI 应用入口 —— 创建 app 实例、注册中间件、引入路由。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.constants import API_PREFIX

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


# ---- 注册子路由（后续按模块扩展） ----
# from src.api.xxx import router as xxx_router
# app.include_router(xxx_router, prefix=API_PREFIX)

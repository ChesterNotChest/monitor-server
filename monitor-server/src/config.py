"""
应用配置 —— 从 .env 文件加载。
"""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 应用 ---
    APP_NAME: str = "Monitor Server"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=True, validation_alias="APP_DEBUG")

    # --- 数据库 ---
    DATABASE_URL: str = "sqlite:///./monitor.db"

    # --- 服务 ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- RTMP / SRS ---
    RTMP_HOST: str = "127.0.0.1"
    RTMP_PORT: int = 1935
    RTMP_DEBUG: bool = False
    SRS_HOST: str = "127.0.0.1"
    SRS_RTMP_PORT: int = 1935
    SRS_HTTP_PORT: int = 8080

    # --- Node WebSocket ---
    WSS_NODE_PORT: int = 8000
    WSS_NODE_DEBUG: bool = False

    # --- 本地 View 流调试 ---
    DEBUG_WEB_STREAM: bool = False


settings = Settings()

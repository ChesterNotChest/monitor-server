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

    # --- 人脸图片存储 ---
    FACE_IMAGE_DIR: str = "./face_images"
    MAX_AVATAR_SIZE: int = 10 * 1024 * 1024  # 10MB

    # --- 服务 ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()

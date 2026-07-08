"""
应用配置 —— 从 .env 文件加载。
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- 应用 ---
    APP_NAME: str = "Monitor Server"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # --- 数据库 ---
    DATABASE_URL: str = "sqlite:///./monitor.db"

    # --- 服务 ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"


settings = Settings()

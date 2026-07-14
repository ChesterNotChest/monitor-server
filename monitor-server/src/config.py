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

    # --- 录制回放 ---
    CACHE_DURATION_SECONDS: int = 30     # 环形缓冲区保留时长
    RECORD_STOP_SILENCE_SECONDS: int = 60  # 连续无告警多少秒后停止录制

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
    SRS_PUBLIC_HOST: str | None = None
    SRS_PUBLIC_RTMP_PORT: int | None = None
    SRS_PUBLIC_HTTP_PORT: int | None = None

    # --- Stream readiness ---
    STREAM_READY_TIMEOUT: float = 30.0
    STREAM_PROBE_TIMEOUT: float = 8.0
    STREAM_READY_INTERVAL: float = 1.0

    # --- AI 推理管线 ---
    FPS_TARGET: int = 15
    YOLO_DEVICE: str = "cpu"
    YOLO_CONFIDENCE: float = 0.5
    YOLO_MODEL_PATH: str = "src/third-party/yolo/yolo11n.pt"
    YOLO_DEVICE: str = "cpu"
    STREAM_RECONNECT_MAX_RETRIES: int = 10
    FACE_MATCH_TOLERANCE: float = 0.42
    FACE_MATCH_MARGIN: float = 0.06
    FACE_SKIP_FRAMES: int = 5
    YAMNET_THRESHOLD: float = 0.5
    DWELL_TIME_DEFAULT: int = 10
    DENSITY_DEFAULT: float = 0.6
    LEAVE_FRAMES_DEFAULT: int = 5
    ALERT_CHECK_INTERVAL: int = 5
    ALERT_EVENT_TTL: int = 5
    ALERT_COOLDOWN: int = 30
    BYTETRACK_TRACK_THRESH: float = 0.5
    BYTETRACK_MATCH_THRESH: float = 0.8

    # --- Node WebSocket ---
    WSS_NODE_PORT: int = 8000
    WSS_NODE_DEBUG: bool = False

    # --- 本地 View 流调试 ---
    DEBUG_WEB_STREAM: bool = False
    DEBUG_FLV_TRANSMIT: bool = False
 # --- 管理员账户 ---
    ADMIN_DEFAULT_PASSWORD: str = "admin123"

     # --- 钉钉通知 ---
    DINGTALK_WEBHOOK_URL: str = ""
    ESCALATION_TIMEOUT_SECONDS: int = 60
    ESCALATION_MAX_LEVELS: int = 2

    # --- 日报 AI 洞察 ---
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_REPORT_MODEL: str = "deepseek-v4-flash"

    # --- 录制（.env 默认值，运行时可通过 API 覆盖并持久化） ---
    RECORDING_MAX_SECONDS: int = 10
    RECORDING_WIND_DOWN_SECONDS: int = 10

    # --- JWT 认证 ---
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8


settings = Settings()

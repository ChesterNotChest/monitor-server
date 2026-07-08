"""
SQLAlchemy 扩展 —— 引擎、会话、基类统一管理。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类 —— 所有 model 继承自此。"""
    pass


def get_db():
    """FastAPI 依赖注入 —— 获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

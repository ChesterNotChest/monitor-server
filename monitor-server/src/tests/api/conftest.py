"""API 测试 fixtures —— 使用测试数据库替换生产依赖。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.app import app
from src.extensions import Base, get_db
from src.service.auth_task import hash_password
from src.repository.user_repo import UserRepo
from src.constants import Role


@pytest.fixture(scope="session")
def engine():
    """会话级 SQLite 引擎，为 API 测试创建表。"""
    _engine = create_engine(
        "sqlite:///./test_api_monitor.db",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


@pytest.fixture
def db(engine):
    """函数级 Session，事务隔离。"""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    transaction.rollback()
    session.close()
    connection.close()


@pytest.fixture
def client(db):
    """TestClient，使用测试数据库会话替换 FastAPI 依赖。"""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(db):
    """获取 admin 用户的 JWT token，供 API 测试鉴权使用。"""
    from src.service.auth_task import login
    repo = UserRepo(db)
    if not repo.by_username("admin"):
        repo.create(
            username="admin",
            password_hash=hash_password("admin"),
            role=Role.OPERATOR,
            is_active=True,
        )
    token_data = login(db, "admin", "admin")
    return token_data["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    """带 admin token 的 Authorization headers。"""
    return {"Authorization": f"Bearer {admin_token}"}

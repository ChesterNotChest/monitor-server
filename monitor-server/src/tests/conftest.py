"""全局测试 fixtures —— SQLite 内存数据库 + 事务隔离。"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.extensions import Base
from src.config import settings


@pytest.fixture(scope="session")
def engine():
    """会话级 SQLite 引擎，所有测试共享。"""
    _engine = create_engine(
        "sqlite:///./test_monitor.db",
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
    """函数级 Session，每个测试事务隔离，结束后 rollback。"""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    transaction.rollback()
    session.close()
    connection.close()

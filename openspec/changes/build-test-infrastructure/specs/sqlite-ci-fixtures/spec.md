## ADDED Requirements

### Requirement: conftest.py 全局 fixtures
系统 SHALL 在 `tests/conftest.py` 中提供共享 fixtures：会话级 SQLite engine、函数级 db session（事务回滚隔离）。

#### Scenario: engine fixture 创建数据库
- **WHEN** pytest 启动测试会话
- **THEN** 自动创建 SQLite 文件数据库，执行 `Base.metadata.create_all`

#### Scenario: db fixture 提供隔离事务
- **WHEN** 每个测试函数请求 `db` fixture
- **THEN** 获得独立的事务 Session，测试结束后自动 rollback

#### Scenario: 会话结束时清理
- **WHEN** pytest 测试会话结束
- **THEN** 自动 `drop_all` 表并关闭 engine

### Requirement: SQLite 外键约束开启
系统 SHALL 在 conftest 中确保 SQLite 的 `PRAGMA foreign_keys=ON` 已开启，使 FK 约束在测试中生效。

#### Scenario: FK 约束违反时抛异常
- **WHEN** 测试向有 FK 约束的字段插入不存在的引用
- **THEN** SQLite 抛出 `IntegrityError`，与 PostgreSQL 行为一致

### Requirement: pytest 配置
系统 SHALL 提供 `pytest.ini` 或 `pyproject.toml [tool.pytest]` 配置，指定测试目录和选项。

#### Scenario: 运行全部测试
- **WHEN** 在项目根目录运行 `pytest`
- **THEN** 自动发现 `tests/` 下所有 `test_*.py` 文件并运行

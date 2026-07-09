## Context

项目采用 SQLAlchemy 2.0 + FastAPI，当前测试基础几乎为零。需要一套从单元测试到集成测试再到 E2E 的完整测试体系，同时将测试组织规范固化到 openspec 中作为团队标准。

## Goals / Non-Goals

**Goals:**
- 建立清晰的测试目录层级规范，镜像源码包结构
- 全部测试统一为 pytest 格式，支持 `pytest tests/` 一键运行
- SQLite 内存/文件数据库驱动 CI，零外部依赖
- 组 A + 组 B 全部 13 个 Repo 的冒烟测试 + 异常路径覆盖
- 提供一个多 Repo 协作的集成测试示例

**Non-Goals:**
- 不测试 Service 层（尚未构建）
- 不测试 API 路由（尚未构建）
- 不引入 Docker 或外部数据库
- 不设定覆盖率阈值（后续阶段引入）

## Decisions

### 1. 测试目录组织规范（写入 openspec）

```
tests/
├── conftest.py                  # 全局 fixtures（engine, Session, 建表）
├── repository/                  # 镜像 src/repository/
│   ├── _test.md                 # 说明文档
│   ├── test_node_repo.py
│   ├── test_video_device_repo.py
│   ├── test_audio_device_repo.py
│   ├── test_monitor_view_repo.py
│   ├── test_electronic_fence_repo.py
│   ├── test_entity_type_repo.py
│   ├── test_action_type_repo.py
│   ├── test_sound_type_repo.py
│   ├── test_named_person_repo.py
│   ├── test_alert_group_repo.py
│   ├── test_exception_def_repo.py
│   ├── test_response_action_repo.py
│   ├── test_situation_event_repo.py
│   └── test_integration.py      # 多 Repo 协作集成测试
├── service/                     # 预留
│   ├── _test.md
│   └── video_module/
│       └── _test.md
├── api/                         # 预留
│   └── _test.md
└── e2e/                         # 端到端测试
    └── _test.md
```

**组织规则：**

| 规则 | 说明 |
|---|---|
| 镜像结构 | `tests/<package>/` 对应 `src/<package>/`，子模块按 `service/video_module/` 组织 |
| 单一模块测试 | 放入对应包目录，如 `tests/repository/test_node_repo.py` |
| 多模块测试 | 放入主要被测试模块的目录，例如涉及 3 个 repo 的集成测试 → `tests/repository/test_integration.py` |
| E2E 测试 | 统一 `tests/e2e/`，不与模块耦合 |
| 说明文档 | 每个包目录维护 `_test.md`，简记该目录测试的覆盖范围和注意事项 |
| 命名约定 | pytest 发现规则：`test_*.py`（冒烟/单元）、`test_integration*.py`（集成）；`_test.md` 不参与测试运行 |

### 2. SQLite CI 架构

```python
# tests/conftest.py

@pytest.fixture(scope="session")
def engine():
    """会话级 SQLite 引擎，所有测试共享。"""
    engine = create_engine("sqlite:///./test_monitor.db", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture
def db(engine):
    """函数级 Session，每个测试事务隔离。"""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    yield session
    transaction.rollback()       # 回滚，不污染数据库
    session.close()
    connection.close()
```

| 决策 | 选择 | 理由 |
|---|---|---|
| 数据库 | SQLite 文件 `test_monitor.db` | 零配置，CI 中无需任何服务 |
| 隔离策略 | 每个测试一个事务，结束后 rollback | 无需重建表，速度快 |
| Session 创建 | `SessionLocal(bind=connection)` | 复用现有工厂，不改代码 |
| 表管理 | session 级 `create_all` + drop | 确保 schema 干净 |

### 3. 冒烟测试模式

每个 Repo 测试文件遵循统一结构：

```python
# tests/repository/test_foo_repo.py

class TestFooRepo:
    """FooRepo 冒烟测试。"""

    def test_create_and_get(self, db):
        repo = FooRepo(db)
        obj = repo.create(name="test")
        assert obj.id is not None
        assert repo.get(obj.id).name == "test"

    def test_create_and_delete(self, db):
        repo = FooRepo(db)
        obj = repo.create(name="test")
        assert repo.delete(obj.id) is True
        assert repo.get(obj.id) is None

    def test_get_nonexistent(self, db):
        repo = FooRepo(db)
        assert repo.get(99999) is None

    def test_delete_nonexistent(self, db):
        repo = FooRepo(db)
        assert repo.delete(99999) is False

    def test_paginate(self, db):
        repo = FooRepo(db)
        for i in range(5):
            repo.create(name=f"test-{i}")
        items, total = repo.paginate(page=1, page_size=3)
        assert len(items) == 3
        assert total == 5

    # 异常路径
    def test_unique_constraint_violation(self, db):
        repo = FooRepo(db)
        repo.create(name="dup")
        with pytest.raises(IntegrityError):
            repo.create(name="dup")
            db.flush()    # 有些 DB 在 commit 时才抛

    def test_nullable_field(self, db):
        repo = FooRepo(db)
        obj = repo.create()  # 只依赖默认值
        assert obj is not None
```

### 4. 集成测试示例

```python
# tests/repository/test_integration.py

def test_view_lifecycle_device_occupation(db):
    """集成测试：创建 View → 设备被占用 → 删除 View → 设备释放"""
    node_repo = NodeRepo(db)
    video_repo = VideoDeviceRepo(db)
    audio_repo = AudioDeviceRepo(db)
    view_repo = MonitorViewRepo(db)

    # 1. 创建 Node + Device
    node = node_repo.create(token="integration-token")
    video = video_repo.create(name="int-cam", node_id=node.id)
    audio = audio_repo.create(name="int-mic", node_id=node.id)

    # 2. 设备未被占用
    assert view_repo.device_in_use(video_id=video.id) is False

    # 3. 创建 View
    view = view_repo.create(video_id=video.id, audio_id=audio.id)
    assert view_repo.device_in_use(video_id=video.id) is True
    assert view_repo.device_in_use(audio_id=audio.id) is True

    # 4. 删除 View，设备释放
    view_repo.delete(view.id)
    assert view_repo.device_in_use(video_id=video.id) is False
    assert view_repo.device_in_use(audio_id=audio.id) is False

    # cleanup
    audio_repo.delete(audio.id)
    video_repo.delete(video.id)
    node_repo.delete(node.id)
```

## Risks / Trade-offs

- **SQLite vs PostgreSQL 行为差异**：某些约束（如 FK 的 `ON DELETE RESTRICT`）在 SQLite 中需 `PRAGMA foreign_keys=ON` → conftest 中自动开启
- **事务回滚覆盖不了 `commit()` 的行为**：后续 service 层测试需要真正 commit 的场景时，改用 session 级 `create_all` + 测试后 `drop_all`
- **测试文件数量随模块增长**：命名约定 `test_*.py` 已覆盖 pytest 自动发现，无需维护显式注册

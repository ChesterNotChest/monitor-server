## Context

项目已有 13 个 SQLAlchemy 模型（详见 `src/models/`），均继承 `Base`（`DeclarativeBase`）。数据库会话通过 `extensions.get_db()` 依赖注入获取。当前 `src/repository/` 为空，需要建立统一的数据访问层。

系统规划了 8 大模块：人员管理、监控总览、智能识别、告警处置、日志回放、设备管理、权限管理、统计报表。每个模块都有大量数据查询需求，需要一个可扩展的 Repository 架构。

## Goals / Non-Goals

**Goals:**
- 提供泛型 `BaseRepo[T]` 基类，封装所有模型的通用 CRUD 操作
- 按业务域分成**组 A（设备/基础）**和**组 B（人员/告警/事件）**，支持两人并行开发
- MonitorViewRepo 支持 View 创建/删除时的流占用检查
- 所有 Repository 通过构造函数注入 `Session`，便于 service 层使用和 mock 测试

**Non-Goals:**
- 不创建 Service 层、API 路由层、Schema 层
- 不修改 Models 或 Extensions
- 不引入 ORM 之外的数据库抽象（如 Redis 缓存）
- 不实现 soft-delete（软删除），当前全部使用物理删除

## Decisions

### 1. 泛型基类设计

选择 `Generic[T]` 泛型基类模式：

```python
T = TypeVar("T")

class BaseRepo(Generic[T]):
    model: type[T]

    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> T | None: ...
    def all(self, *, offset=0, limit=100) -> list[T]: ...
    def create(self, **kwargs) -> T: ...
    def delete(self, id: int) -> bool: ...
    def count(self) -> int: ...
    def exists(self, id: int) -> bool: ...
    def paginate(self, page=1, page_size=20) -> tuple[list[T], int]: ...
```

| 决策 | 选择 | 理由 |
|---|---|---|
| 泛型绑定方式 | `model: type[T]` 类变量 | 静态类型检查完整，IDE 自动补全 |
| 分页默认值 | page=1, page_size=20 | 与 `constants.py` 中 `DEFAULT_PAGE=1, DEFAULT_PAGE_SIZE=20` 保持一致 |
| Repository 粒度 | 每个 Model 一个 Repo | 复用基类通用方法，继承成本极低（3 行定义一个 Repo） |
| Session 注入方式 | 构造函数注入 `__init__(self, db)` | Service 层创建 Repo 实例时传入 session，生命周期清晰 |
| 返回值类型 | 返回 Model 实例而非 dict | 保持 ORM 完整能力（关系加载、属性访问），service/schema 层负责序列化 |

### 2. 组划分策略

| 组 | 模型 | 业务域 | 人员 |
|---|---|---|---|
| **组 A** | Node、VideoDevice、AudioDevice、MonitorView、ElectronicFence、EntityType、ActionType、SoundType | 设备管理、监控总览、AI 检测枚举 | 人员 A |
| **组 B** | NamedPerson、AlertGroup、ExceptionDef、ResponseAction、SituationEvent | 人员管理、告警处置、日志回放 | 人员 B |

划分原则：组 A 是"基础设施 + 枚举"（被组 B 引用），组 B 是"业务核心 + 事件"（依赖组 A 的 FK）。组 B 的 Repo 在查询时可能 JOIN 到组 A 的表。

### 3. View 流管理策略

View 创建/删除时的"推流占用检查"采用**推导模式**（不存储 `is_streaming` 字段）：

```
VideoDevice/AudioDevice 是否被占用 = MonitorView 表中有无引用该设备的记录
```

| 方案 | 选择 | 理由 |
|---|---|---|
| 显式字段 `is_streaming` | ❌ | 需手动维护一致性，并发场景容易出 bug |
| MonitorView 表推导 | ✅ | 单一信源，`ViewRepo.device_in_use(video_id)` 一次查询即可判断 |

MonitorViewRepo 额外提供：
- `device_in_use(*, video_id, audio_id) -> bool` — 检查设备是否被任何 View 占用
- `find_by_device(*, video_id, audio_id) -> list[MonitorView]` — 列出使用该设备的所有 View

### 4. Session 事务策略

- Repository 层仅 `flush()`，不 `commit()`
- `commit()` 统一由 Service 层（后续创建）调用
- 这保证了多个 Repo 操作可以在同一个事务中

## Risks / Trade-offs

- **N+1 查询风险**：`all()` 返回 ORM 对象，service 层遍历访问 relationship 时可能触发 N+1 → Repository 层的方法默认使用 `selectinload` 可缓解
- **基类过度抽象**：如果某个模型不需要 `create(**kwargs)` 模式（需要特殊校验）→ 子类直接重写方法，基类不强制
- **并发删除 View 时的竞争**：`device_in_use` 和 `delete` 之间可能有另一个请求创建 View → 当前使用 SQLite 默认的串行写锁已覆盖，PostgreSQL 迁移后可用 `SELECT FOR UPDATE` 加固

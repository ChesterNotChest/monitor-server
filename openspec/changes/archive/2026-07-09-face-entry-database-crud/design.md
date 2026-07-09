## Context

当前系统使用 SQLAlchemy ORM + SQLite，`NamedPerson` 模型仅有 `id`、`avatar_path`、`feat_json_id`、`created_at` 四个字段，缺少人物姓名。`BaseRepo` 提供了通用查询与创建/删除，但缺少更新方法。尚未有 API 路由和文件上传能力。

**约束:**
- 技术栈：Python 3.11+、FastAPI、SQLAlchemy 2.0、SQLite（开发调试阶段）
- ORM 模型使用 SQLAlchemy 2.0 Mapped 风格（与现有代码一致）
- 分层架构遵循项目 Spec 规范：

| 层 | 位置 | 规范来源 |
|---|---|---|
| 网络层 (API Router) | `src/network/api/` | `network-layer` spec |
| 服务层 (门户+内部逻辑) | `src/service/*_task.py` + `*_module/` | `service-layer` spec |
| Schema 层 (请求/响应模型) | `src/schema/http/` | `schema-convention` spec |
| 仓库层 (数据访问) | `src/repository/` | `repo-base` spec |
| 模型层 (ORM) | `src/models/` | 各 model spec |

- **关键规则**：Router 不直接操作 repository（即使是简单读操作也通过 `*_task.py` 包装）；task 通过 `db: Session` 参数接收会话
- 图片存储：本地磁盘，数据库仅存相对路径
- 严格遵守"仅完成入库相关功能，无额外扩展"

## Goals / Non-Goals

**Goals:**
- NamedPerson 模型新增 `name` 字段（唯一、非空），作为人物标识
- BaseRepo 新增 `update` 方法，支持按主键部分字段更新
- 实现人脸图片文件存储服务：上传到 `face_images/person_{id}/`，返回相对路径
- 实现命名人物的完整 RESTful CRUD API + 头像上传，遵循三层架构规范

**Non-Goals:**
- 不切换数据库引擎（继续使用 SQLite，MySQL 留待后续）
- 不实现人脸检测/识别/特征提取逻辑（已有 `feat_json_id` 字段预留）
- 不实现批量导入/导出
- 不实现认证鉴权
- 不修改其他已有模型或 Repository

## Decisions

### 1. 图片存储：项目根目录 `face_images/` + 相对路径

**选择**: 人脸图片存储在项目根目录的 `face_images/` 下，按 `person_{id}/avatar.{ext}` 组织。数据库 `avatar_path` 存相对路径（如 `person_1/avatar.jpg`）。

**路径解析**: `src/config.py` 中 `FACE_IMAGE_DIR` 默认值为 `./face_images`，运行时相对于工作目录（即项目根目录 `monitor-server/`）。服务层通过 `settings.FACE_IMAGE_DIR` 获取绝对路径存储文件，对外仅暴露相对路径。

**理由**:
- 用户明确要求"SQL 内存人脸图片的相对路径"
- 按人物 ID 分目录，便于管理和扩展（后续可存多张人脸图）
- 相对路径便于跨环境迁移
- 与项目现有 `avatar_path` 字段设计一致

**目录示例:**

```
monitor-server/
└── face_images/          ← FACE_IMAGE_DIR 默认值
    ├── person_1/
    │   └── avatar.jpg    ← DB 存: person_1/avatar.jpg
    ├── person_2/
    │   └── avatar.png    ← DB 存: person_2/avatar.png
    └── ...
```

### 2. 分层调用链

**选择**: 严格遵循三层规范，Router → task 门户 → repository / 图片服务。

```
src/network/api/named_person.py          ← Router: 解析请求，调用 task，返回响应
        │
        ▼
src/service/named_person_task.py         ← 门户: 编排流程，接收 db: Session
        │
        ├──▶ src/repository/named_person_repo.py       ← 数据库 CRUD
        └──▶ src/service/named_person_module/
             └── face_image.py                          ← 图片文件 I/O
```

**理由**: 遵循 `network-layer` spec "Router 不直接操作数据库" 和 `service-layer` spec "task 负责编排业务流程"。即使是 `GET /persons` 这样的简单读操作，也通过 `named_person_task.list_persons(db, page, page_size)` 包装，不直接在 Router 中调用 `NamedPersonRepo`。

### 3. 服务层：门户 + 内部逻辑包

**选择**:

- `src/service/named_person_task.py` — 业务门户，提供 `create_person(db, name)`、`list_persons(db, page, page_size)`、`get_person(db, id)`、`update_person(db, id, name)`、`delete_person(db, id)`、`upload_avatar(db, id, file)`
- `src/service/named_person_module/face_image.py` — 内部逻辑（被 task 调用），提供 `save_avatar(person_id, file) -> str`、`delete_avatar(person_id) -> None`

**理由**: 遵循 `service-layer` spec 的 `*_task.py` + `*_module/` 结构。命名人物的 CRUD 逻辑简单（单表操作），但图片 I/O 是独立的文件系统操作，封装到 `named_person_module/face_image.py` 作为内部逻辑模块。task 通过 `db: Session` 参数接收会话。

### 4. update 方法设计

**选择**: `BaseRepo.update(id, **kwargs) -> T | None` — 按主键查找，仅更新 kwargs 中非 None 字段，flush 但不 commit。

**理由**: 与现有 `create(**kwargs)` 风格一致。Commit 由 Service 层控制。

### 5. 模型扩展：name 字段

**选择**: 新增 `name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)`。

**理由**: `unique=True` 保证姓名不重复。128 字符足够容纳中英文姓名。

## Risks / Trade-offs

- **[R] 图片文件与数据库不一致**: 文件删除失败但数据库记录已删除 → 定期清理孤儿文件脚本（非本次范围）
- **[R] name 唯一约束**: 同名人物无法录入 → 可接受，真实场景中通过额外编号区分，后续可扩展
- **[R] SQLite 并发限制**: 单文件锁 → 当前为单机开发/测试场景，不构成瓶颈；切换 MySQL 仅需改连接串

## Migration Plan

1. 安装 `python-multipart` 依赖
2. 创建 `src/network/api/`、`src/schema/http/` 目录（如尚未存在）
3. 更新 `src/config.py` 新增 `FACE_IMAGE_DIR` 和 `MAX_AVATAR_SIZE` 配置
4. 扩展 `NamedPerson` 模型（新增 `name` 列）
5. 新增 `BaseRepo.update` 方法
6. 新增 `src/service/named_person_module/face_image.py` 图片存储内部逻辑
7. 新增 `src/service/named_person_task.py` 门户函数
8. 新增 `src/schema/http/named_person.py` Pydantic 模型
9. 新增 `src/network/api/named_person.py` 路由并注册到 `app.py`
10. 更新现有测试，新增测试
11. 删除旧 SQLite 数据库文件，重启应用自动重建表结构

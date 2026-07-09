## Context

当前系统使用 SQLAlchemy ORM + SQLite，`NamedPerson` 模型仅有 `id`、`avatar_path`、`feat_json_id`、`created_at` 四个字段，缺少人物姓名。`BaseRepo` 提供了通用查询与创建/删除，但缺少更新方法。尚未有 API 路由和文件上传能力。

**约束:**
- 技术栈：Python 3.11+、FastAPI、SQLAlchemy 2.0、SQLite（开发调试阶段）
- ORM 模型使用 SQLAlchemy 2.0 Mapped 风格（与现有代码一致）
- 分层模式：API → Service → Repository → ORM（遵循项目现有 `explore_result.md` 约定的架构）
- Schema 层独立于 API 层：Pydantic 模型放 `src/schema/`
- 图片存储：本地磁盘，数据库仅存相对路径
- 严格遵守"仅完成入库相关功能，无额外扩展"

## Goals / Non-Goals

**Goals:**
- NamedPerson 模型新增 `name` 字段（唯一、非空），作为人物标识
- BaseRepo 新增 `update` 方法，支持按主键部分字段更新
- 实现人脸图片文件存储服务：上传到 `face_images/person_{id}/`，返回相对路径
- 实现命名人物的完整 RESTful CRUD API（创建、读取列表/详情、更新、删除）+ 头像上传
- 遵循项目现有分层惯例：API 路由放 `src/api/`，Schema 放 `src/schema/`

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

### 2. update 方法设计

**选择**: `BaseRepo.update(id, **kwargs) -> T | None` — 按主键查找，仅更新 kwargs 中非 None 字段，flush 但不 commit。

**理由**: 与现有 `create(**kwargs)` 风格一致，保持 Repository 模式的一致性。Commit 由 Service 层控制。

### 3. API 设计：RESTful，头像上传独立端点

**选择**:
- 命名人物 CRUD: `/api/v1/persons`（集合）、`/api/v1/persons/{id}`（单个）
- 头像上传: `POST /api/v1/persons/{id}/avatar`（multipart/form-data）
- API 路由文件: `src/api/named_person.py`（遵循现有 flat 结构）
- Pydantic Schema: `src/schema/named_person.py`

**理由**: 与项目现有 `src/api/` 下 flat 文件 + `src/schema/` 独立管理的约定一致。

### 4. 模型扩展：name 字段

**选择**: 新增 `name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)`。

**理由**: `unique=True` 保证姓名不重复，作为业务标识。128 字符足够容纳中英文姓名。

### 5. 服务层：face_image_service.py

**选择**: 新建 `src/service/face_image_service.py`，提供 `save_avatar()` 和 `delete_avatar()` 两个函数。与现有 `video_task.py` 同为 service 层入口文件。

**理由**: 图片存储职责独立，不涉及多模块协作，无需像 `video_task.py + video_module/` 那样拆分。

## Risks / Trade-offs

- **[R] 图片文件与数据库不一致**: 文件删除失败但数据库记录已删除 → 定期清理孤儿文件脚本（非本次范围）
- **[R] name 唯一约束**: 同名人物无法录入 → 可接受，真实场景中通过额外编号区分，后续可扩展
- **[R] SQLite 并发限制**: 单文件锁 → 当前为单机开发/测试场景，不构成瓶颈；切换 MySQL 仅需改连接串，SQLAlchemy 已封装引擎差异

## Migration Plan

1. 安装 `python-multipart` 依赖
2. 更新 `src/config.py` 新增 `FACE_IMAGE_DIR` 和 `MAX_AVATAR_SIZE` 配置
3. 扩展 `NamedPerson` 模型（新增 `name` 列）
4. 新增 `BaseRepo.update` 方法
5. 新增 `face_image_service.py` 图片存储服务
6. 新增 `src/schema/named_person.py` Pydantic 模型
7. 新增 `src/api/named_person.py` 路由并注册到 `app.py`
8. 更新现有测试，新增测试
9. 删除旧 SQLite 数据库文件，重启应用自动重建表结构

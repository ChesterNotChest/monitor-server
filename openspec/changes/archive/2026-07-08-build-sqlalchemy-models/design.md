## Context

当前 `src/models/` 仅有 `example.py` 模板文件，项目使用原生 SQLAlchemy 2.0 `DeclarativeBase`（`src/extensions.py` 中的 `Base`），而非 Flask-SQLAlchemy 的 `db.Model`。`example.py` 展示了 Flask-SQLAlchemy 风格（`db.Model`、`db.Column`），需要将其适配为当前项目的 SQLAlchemy 范式。监控系统涉及计算机节点、音视频采集设备、AI 检测结果（YOLO/SlowFast/YAMNet）、异常判定与响应等多个领域模型。

## Goals / Non-Goals

**Goals:**
- 按照 SQLAlchemy 2.0 `DeclarativeBase` 范式定义所有业务表模型
- 每个模型独立一个 `.py` 文件，便于维护
- 正确建立外键约束、索引与多对多关联
- 定义 AI 检测相关的枚举常量（YOLO 实体、SlowFast 行为、YAMNet 声音）

**Non-Goals:**
- 不创建 CRUD 仓库层（将在后续 change 中实现）
- 不创建 API 路由（将在后续 change 中实现）
- 不包含 Alembic 迁移脚本（初始 schema 由 `Base.metadata.create_all` 处理）

## Decisions

| 决策 | 选择 | 备选方案及弃用理由 |
|---|---|---|
| ORM 基类 | `src.extensions.Base`（`DeclarativeBase`） | Flask-SQLAlchemy `db.Model`：项目未使用 Flask，需保持一致 |
| 列定义风格 | `mapped_column()` + 类型注解（SQLAlchemy 2.0 推荐） | `db.Column()`：旧式写法，SQLAlchemy 2.0 已推荐 `mapped_column` |
| 枚举存储 | 数据库存整数值 + Python Enum 类 | 存字符串：浪费空间，不利于数值比较排序 |
| 异常关联设计 | 独立的关联表（exception_entities 等），支持多对多 | JSON 字段存关联：无法利用外键约束与索引，查询效率低 |
| 文件组织 | 每个模型一个 `.py` 文件 | 单文件 models.py：随业务增长变得难以维护 |
| 坐标存储 | `coords` 使用 `Text` 类型存 JSON 字符串 | PostGIS Geometry：围栏场景多边形足够，避免引入空间扩展 |

## Risks / Trade-offs

- **模型字段可能后续需要调整**：当前为第一版设计，AI 检测实际对接时可能需要增减字段 → 使用 SQLite 开发阶段可快速重建，生产环境通过 Alembic 迁移
- **多对多关联表查询性能**：当异常事件数据量大时，JOIN 查询可能变慢 → 可通过在关联表外键上建索引缓解，后续添加 Redis 缓存
- **coords 字段存 JSON 字符串**：不支持空间查询 → 当前需求仅为存储与回显，后续如需空间查询可升级为 PostGIS

## Open Questions

- 电子围栏的 `coords` 具体格式？（多边形顶点数组？矩形两点？）→ 默认采用 `[[lon,lat], ...]` 多边形格式，后续按需调整
- 异常触发条件的具体设计？→ 标记为 TODO，在异常业务 service 层实现，不在本次模型层处理
- `PersonID` 的 `featJsonID` 指向哪个向量存储？→ 预留字符串字段，后续对接特征向量服务

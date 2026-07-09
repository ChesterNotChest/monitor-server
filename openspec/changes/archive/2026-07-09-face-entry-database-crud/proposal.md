## Why

当前系统缺少人脸录入的完整入库链路：`NamedPerson` 模型没有人物姓名字段，`BaseRepo` 不支持更新操作，也没有人脸图片的文件存储与上传机制。需要补齐命名人物信息与图片的增删改查能力。数据库继续使用 SQLite（开发调试阶段），MySQL 等生产库切换留待后续。

## What Changes

- 扩展 `NamedPerson` 模型，新增 `name`（人物姓名）唯一字段
- `BaseRepo` 泛型基类新增 `update` 方法
- `NamedPersonRepo` 新增按姓名查询方法
- 新增人脸图片文件存储服务，图片存储在项目根目录 `face_images/` 下的 `person_{id}/avatar.{ext}`，数据库仅存相对路径
- 新增命名人物 RESTful API：`POST /api/v1/persons`（录入）、`GET /api/v1/persons`（列表）、`GET /api/v1/persons/{id}`（详情）、`PUT /api/v1/persons/{id}`（更新）、`DELETE /api/v1/persons/{id}`（删除）、`POST /api/v1/persons/{id}/avatar`（上传头像）

## Capabilities

### New Capabilities

- `named-person-crud`: 命名人物信息的增删改查 RESTful API，包括录入时同时上传头像图片
- `face-image-storage`: 人脸图片文件存储服务，支持文件上传、替换、删除，返回相对路径存入数据库

### Modified Capabilities

- `named-person-model`: 新增 `name` 字段（唯一、非空），作为人物的主要标识
- `repo-base`: 新增 `update` 方法，支持按主键更新记录字段

## Impact

- **模型层**: `src/models/named_person.py` — 新增 `name` 字段
- **仓库层**: `src/repository/base.py` — 新增 `update` 方法；`src/repository/named_person_repo.py` — 新增按名查询
- **服务层**: 新增 `src/service/named_person_task.py`（门户函数）+ `src/service/named_person_module/`（内部逻辑包，含 `face_image.py`）— 遵循 `service-layer` 规范的 `*_task.py` + `*_module/` 约定，门户编排 CRUD 流程，内部逻辑封装图片文件操作
- **Schema 层**: 新增 `src/schema/http/named_person.py` — Pydantic 请求/响应模型，遵循 `schema-convention` 规范的 HTTP/WSS 分家规则
- **网络层**: 新增 `src/network/api/named_person.py` — CRUD 路由，遵循 `network-layer` 规范，Router 通过 `named_person_task.py` 门户函数间接操作，不直接访问 repository
- **配置**: `src/config.py` — 新增 `FACE_IMAGE_DIR`（默认 `./face_images`）和 `MAX_AVATAR_SIZE`（默认 10MB）
- **依赖**: 新增 `python-multipart`（文件上传）

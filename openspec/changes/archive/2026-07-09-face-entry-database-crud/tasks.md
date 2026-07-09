## 1. 依赖与配置

- [x] 1.1 安装文件上传依赖：`pip install python-multipart`
- [x] 1.2 确保 `src/network/api/`、`src/schema/http/` 目录存在（含 `__init__.py`），若不存在则创建
- [x] 1.3 更新 `src/config.py`，新增 `FACE_IMAGE_DIR`（人脸图片存储根目录，默认 `./face_images`，位于项目根目录下）和 `MAX_AVATAR_SIZE`（默认 10MB，单位字节）

## 2. 模型层

- [x] 2.1 扩展 `src/models/named_person.py`：新增 `name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)` 字段
- [x] 2.2 更新 `src/models/__init__.py` 确认 `NamedPerson` 导入完整

## 3. 仓库层

- [x] 3.1 在 `src/repository/base.py` 的 `BaseRepo` 中新增 `update(id: int, **kwargs) -> T | None` 方法：按 ID 查找，仅更新 kwargs 中非 None 字段，flush 后返回实例，不存在返回 None
- [x] 3.2 在 `src/repository/named_person_repo.py` 中新增 `find_by_name(name: str) -> NamedPerson | None` 方法（用于校验姓名唯一性）

## 4. 服务层

- [x] 4.1 新建 `src/service/named_person_module/__init__.py`
- [x] 4.2 新建 `src/service/named_person_module/face_image.py`：实现 `save_avatar(person_id: int, file: UploadFile) -> str`（保存到 `{FACE_IMAGE_DIR}/person_{id}/avatar.{ext}`，返回相对路径）、`delete_avatar(person_id: int) -> None`（删除目录，幂等）、格式校验（仅 JPEG/PNG）和大小校验（≤ MAX_AVATAR_SIZE）
- [x] 4.3 新建 `src/service/named_person_task.py`：实现 `create_person(db, name)`（调 repo + 唯一性校验）
- [x] 4.4 实现 `list_persons(db, page, page_size)`（委托 repo.paginate）
- [x] 4.5 实现 `get_person(db, id)`（委托 repo.get）
- [x] 4.6 实现 `update_person(db, id, name)`（委托 repo.update + 唯一性校验）
- [x] 4.7 实现 `delete_person(db, id)`（查 avatar_path → 调 face_image.delete_avatar → 调 repo.delete）
- [x] 4.8 实现 `upload_avatar(db, id, file)`（调 face_image.save_avatar → 调 repo.update 更新 avatar_path）

## 5. Schema 层

- [x] 5.1 新建 `src/schema/http/named_person.py`：定义 `PersonCreate`（name 必填）、`PersonUpdate`（name 可选）、`PersonResponse`（id, name, avatar_path, feat_json_id, created_at）
- [x] 5.2 更新 `src/schema/http/__init__.py` 导出新增 schema

## 6. 网络层 API 路由

- [x] 6.1 新建 `src/network/api/named_person.py`，定义 `router = APIRouter(prefix="/persons", tags=["命名人物"])`
- [x] 6.2 实现 `POST /api/v1/persons` — 解析 `PersonCreate`，调用 `named_person_task.create_person(db, name)`，返回 201
- [x] 6.3 实现 `GET /api/v1/persons` — 解析分页参数，调用 `named_person_task.list_persons(db, page, page_size)`，返回 `{items, total, page, page_size}`
- [x] 6.4 实现 `GET /api/v1/persons/{id}` — 调用 `named_person_task.get_person(db, id)`，不存在返回 404
- [x] 6.5 实现 `PUT /api/v1/persons/{id}` — 解析 `PersonUpdate`，调用 `named_person_task.update_person(db, id, name)`，不存在返回 404，冲突返回 409
- [x] 6.6 实现 `DELETE /api/v1/persons/{id}` — 调用 `named_person_task.delete_person(db, id)`，不存在返回 404，成功返回 204
- [x] 6.7 实现 `POST /api/v1/persons/{id}/avatar` — 接收 `UploadFile`，调用 `named_person_task.upload_avatar(db, id, file)`，校验格式和大小
- [x] 6.8 在 `src/app.py` 中注册 `named_person_router`（router 位于 `src/network/api/named_person.py`）

## 7. 测试

- [x] 7.1 更新 `src/tests/repository/test_named_person_repo.py`：所有 create 调用补 `name` 参数，新增 `test_update` 和 `test_find_by_name` 用例
- [x] 7.2 新建 `src/tests/service/test_face_image.py`：测试保存、替换、删除、格式拒绝、大小拒绝
- [x] 7.3 新建 `src/tests/api/test_named_person_api.py`：测试全部 CRUD 端点 + 头像上传端点
- [x] 7.4 运行全部测试，确认无回归：`pytest monitor-server/src/tests/ -v`

## 8. 验证

- [x] 8.1 删除旧 `monitor.db` 文件，启动应用使 SQLAlchemy 自动重建表结构
- [ ] 8.2 通过 `/docs` Swagger 页面手动测试全部端点
- [x] 8.3 验证图片文件正确保存到 `face_images/person_{id}/` 且数据库中存相对路径
- [x] 8.4 验证删除人物时头像文件同步删除

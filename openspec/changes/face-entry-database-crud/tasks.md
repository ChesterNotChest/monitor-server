## 1. 依赖与配置

- [ ] 1.1 安装文件上传依赖：`pip install python-multipart`
- [ ] 1.2 更新 `src/config.py`，新增 `FACE_IMAGE_DIR`（人脸图片存储根目录，默认 `./face_images`，位于项目根目录下）和 `MAX_AVATAR_SIZE`（默认 10MB，单位字节）

## 2. 模型层

- [ ] 2.1 扩展 `src/models/named_person.py`：新增 `name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)` 字段
- [ ] 2.2 更新 `src/models/__init__.py` 确认 `NamedPerson` 导入完整

## 3. 仓库层

- [ ] 3.1 在 `src/repository/base.py` 的 `BaseRepo` 中新增 `update(id: int, **kwargs) -> T | None` 方法：按 ID 查找，仅更新 kwargs 中非 None 字段，flush 后返回实例，不存在返回 None
- [ ] 3.2 在 `src/repository/named_person_repo.py` 中新增 `find_by_name(name: str) -> NamedPerson | None` 方法（用于校验姓名唯一性）

## 4. 人脸图片存储服务

- [ ] 4.1 新建 `src/service/face_image_service.py`：实现 `save_avatar(person_id: int, file: UploadFile) -> str`（保存图片到 `{FACE_IMAGE_DIR}/person_{id}/avatar.{ext}`，返回相对路径）
- [ ] 4.2 实现 `delete_avatar(person_id: int) -> None`（删除 `{FACE_IMAGE_DIR}/person_{id}/` 目录，幂等）
- [ ] 4.3 实现格式校验（仅 JPEG/PNG）和大小校验（≤ MAX_AVATAR_SIZE），不符合抛出 `ValueError`

## 5. Schema 层

- [ ] 5.1 新建 `src/schema/named_person.py`：定义 `PersonCreate`（name 必填）、`PersonUpdate`（name 可选）、`PersonResponse`（id, name, avatar_path, feat_json_id, created_at）
- [ ] 5.2 更新 `src/schema/__init__.py` 导出新增 schema

## 6. API 路由

- [ ] 6.1 新建 `src/api/named_person.py`，定义 `router = APIRouter(prefix="/persons", tags=["命名人物"])`
- [ ] 6.2 实现 `POST /api/v1/persons` — 创建人物（接受 JSON body），校验 name 唯一性，返回 201
- [ ] 6.3 实现 `GET /api/v1/persons` — 分页查询列表，返回 `{items, total, page, page_size}`
- [ ] 6.4 实现 `GET /api/v1/persons/{id}` — 按 ID 查询详情，404 时返回错误
- [ ] 6.5 实现 `PUT /api/v1/persons/{id}` — 更新人物信息，404/409 时返回错误
- [ ] 6.6 实现 `DELETE /api/v1/persons/{id}` — 删除人物及其头像文件（调用 face_image_service），404 时返回错误
- [ ] 6.7 实现 `POST /api/v1/persons/{id}/avatar` — 上传/替换头像（multipart/form-data），校验格式和大小
- [ ] 6.8 在 `src/app.py` 中注册 `named_person_router`

## 7. 测试

- [ ] 7.1 更新 `src/tests/repository/test_named_person_repo.py`：所有 create 调用补 `name` 参数，新增 `test_update` 和 `test_find_by_name` 用例
- [ ] 7.2 新建 `src/tests/service/test_face_image_service.py`：测试保存、替换、删除、格式拒绝、大小拒绝
- [ ] 7.3 新建 `src/tests/api/test_named_person_api.py`：测试全部 CRUD 端点 + 头像上传端点
- [ ] 7.4 运行全部测试，确认无回归：`pytest monitor-server/src/tests/ -v`

## 8. 验证

- [ ] 8.1 删除旧 `monitor.db` 文件，启动应用使 SQLAlchemy 自动重建表结构
- [ ] 8.2 通过 `/docs` Swagger 页面手动测试全部端点
- [ ] 8.3 验证图片文件正确保存到 `face_images/person_{id}/` 且数据库中存相对路径
- [ ] 8.4 验证删除人物时头像文件同步删除

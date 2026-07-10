## 1. 后端清理

- [x] 1.1 删除 `src/schema/http/user.py`
- [x] 1.2 补全 `src/schema/http/exception_schema.py` 的 Field description（ExceptionCreate + ExceptionResponse 共 10 个字段）
- [x] 1.3 运行 `pytest src/tests/api/ -q` 确认无回归（42 passed）

## 2. 前端回退

- [x] 2.1 `types.ts` ExceptionResponse 移除 alert_group / entities / actions / sounds 嵌套字段
- [x] 2.2 `types.ts` 移除 `DetectionTypeRef` 类型（仅 ExceptionResponse 引用，已移除）
- [x] 2.3 `types.ts` 移除 `AlertGroupRef` 类型（仅 ExceptionResponse 引用，已移除）

## 3. 验证

- [x] 3.1 确认项目中无任何对 `schema/http/user.py` 的 import 引用（zero matches）
- [ ] 3.2 确认 `exception_schema.py` 的 Field description 在 Swagger 中可见（手动：启动 server → /docs → 异常定义 Tag）

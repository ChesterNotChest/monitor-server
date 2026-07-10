## 1. 后端清理

- [ ] 1.1 删除 `src/schema/http/user.py`
- [ ] 1.2 补全 `src/schema/http/exception_schema.py` 的 Field description（ExceptionCreate + ExceptionResponse 共 10 个字段）
- [ ] 1.3 运行 `pytest src/tests/api/ -q` 确认无回归

## 2. 前端回退

- [ ] 2.1 `types.ts` ExceptionResponse 移除 alert_group / entities / actions / sounds 嵌套字段
- [ ] 2.2 `types.ts` 移除 `DetectionTypeRef` 类型（如无其他地方引用）
- [ ] 2.3 `types.ts` 移除 `AlertGroupRef` 类型（如无其他地方引用）

## 3. 验证

- [ ] 3.1 确认项目中无任何对 `user.py` 的 import 引用
- [ ] 3.2 确认 `exception_schema.py` 的 Field description 在 Swagger 中可见（手动：启动 server → /docs → 异常定义 Tag）

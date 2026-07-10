## Why

`user.py` 中的 `UserCreate` 和 `UserResponse` 从未被任何 router 引用——用户管理 API 实际使用的是 `auth_schema.py` 的 `UserResponse`（role: string, is_active: bool）。该文件是纯死代码，上次还给它加了误导性的 int role 描述，应直接删除。

`exception_router.py` 实际导入的是精简版 `exception_schema.py`（无嵌套对象），而非完整版 `exception.py`（含 alert_group/entities/actions/sounds 嵌套）。但 `exception_schema.py` 没有任何 Field description，导致 Swagger 中异常规则端点显示空白的字段说明。同时前端 `ExceptionResponse` 上次被错误地加上了嵌套字段，需回退以匹配实际 API 响应。

## What Changes

- **删除 `user.py`**：`UserCreate` 和 `UserResponse` 均为死代码，无任何引用
- **补全 `exception_schema.py` 的 Field description**：ExceptionCreate 和 ExceptionResponse 各字段补充中文 description
- **回退前端 `ExceptionResponse`**：移除上次错误添加的 alert_group / entities / actions / sounds / DetectionTypeRef 嵌套字段，恢复匹配精简版 API 响应
- **运行 pytest 确认无回归**

## Capabilities

### New Capabilities

- `cleanup-dead-user-schema`: 删除 `schema/http/user.py` 死代码

### Modified Capabilities

- `exception-crud-api`: exception_router 实际使用 `exception_schema.py`（精简版），确保该文件有完整的 Field description
- `schema-convention`: 消除 `__init__.py` 导出的 `exception.py` 完整版与实际 API 使用的 `exception_schema.py` 精简版之间的歧义

## Impact

- **Server**: 删除 `src/schema/http/user.py`、修改 `src/schema/http/exception_schema.py`
- **前端**: 修改 `monitor-web/src/api/types.ts` 的 ExceptionResponse，移除嵌套字段
- **无 API 破坏性变更**：API 行为不变，仅删除死代码和修正文档

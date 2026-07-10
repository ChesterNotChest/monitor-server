## Context

当前 `src/schema/http/` 下存在两套 Exception schema：

| 文件 | 用途 | 字段 |
|------|------|------|
| `exception.py` | 完整版，含嵌套（AlertGroupRef, EnumTypeRef） | name, severity, group_id, face_result_id?, fence_event_id?, alert_group?, entities[], actions[], sounds[] |
| `exception_schema.py` | 精简版，仅数字 ID | name, severity, group_id, face_result_id?, fence_event_id?, created_at |

`exception_router.py` 导入的是精简版：`from src.schema.http.exception_schema import ExceptionCreate, ExceptionResponse`。

但 `__init__.py` 导出的是完整版。这形成歧义——Swagger 中看到的是完整版的嵌套结构，但实际 API 返回的是精简版的数字 ID。

同时 `user.py` 的 `UserCreate` / `UserResponse` 无任何 import 引用，router 使用的是 `auth_schema.py` 的版本。

## Goals / Non-Goals

**Goals:**
- 删除 `user.py` 死代码
- `exception_schema.py` 补充 Field description（当前全部缺失）
- 前端 ExceptionResponse 回退至精简版（移除错误添加的嵌套字段）

**Non-Goals:**
- 不合并 `exception.py` 和 `exception_schema.py`
- 不修改 `exception_router.py` 的导入源
- 不动 EventReplay 和 LiveMonitor

## Decisions

### D1：user.py 直接删除

`user.py` 仅含 `UserCreate` 和 `UserResponse`，全项目零引用。直接 `git rm`，`__init__.py` 本身也未导入它。

### D2：前端 ExceptionResponse 回退

回退到与 `exception_schema.py` 一致的精简结构：
```typescript
interface ExceptionResponse {
  id: number;
  name: string;
  severity: number;
  group_id: number | null;
  face_result_id: number | null;
  fence_event_id: number | null;
  created_at: string;
}
```
移除 `alert_group`, `entities`, `actions`, `sounds` 和 `AlertGroupRef`, `DetectionTypeRef`。

### D3：exception_schema.py 补充 description

参照 `exception.py` 已有的 Field description，为 `exception_schema.py` 补充中文描述。

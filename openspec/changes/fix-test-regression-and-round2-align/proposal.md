## Why

上一轮 `complete-server-endpoints` 变更将 View 创建的 `view_task.create_view()` 返回格式从 dict（`{"view": ORM, "srs_urls": dict, "warnings": list}`）改为 Pydantic `ViewResponse` 模型（扁平结构）。该改动导致 `test_view_runtime_hardening.py` 中 2 个测试回归失败——测试代码仍用 dict 下标访问新的 Pydantic 模型。需立即修复以恢复 CI 通过。同时启动第二轮前后端对齐工作，以当前 Swagger 和 server 代码为唯一标准，继续消除前后端差异。

## What Changes

- **修复 `test_create_view_commits_view_and_streaming_state`**：响应从 `{"view": {...}}` 嵌套改为 `ViewResponse` 扁平字段，`response.json()["view"]["id"]` 改为 `response.json()["id"]`
- **修复 `test_create_view_warns_when_raw_streams_are_unavailable`**：`create_view()` 返回 Pydantic model 而非 dict，`result["warnings"][-1]` 改为 `result.warnings[-1]`
- **运行回归测试确认全部通过**
- **第二轮前后端对齐**：以前端程序 `monitor-web` 和 Swagger 为参考，逐模块检查前端 API 调用是否与 server 实际响应匹配，发现并修复不一致

## Capabilities

### New Capabilities

- `test-regression-fix`: 修复因 View 响应格式变更导致的测试回归，确保测试代码与当前 Pydantic 响应模型匹配
- `round2-frontend-alignment`: 第二轮前后端对齐——以前端已实现的 API 调用为基准，对照 Swagger 验证请求参数、响应结构、错误处理的一致性

### Modified Capabilities

- `view-management`: 测试代码中对 `create_view()` 返回值的访问方式需与 `ViewResponse` 模型一致

## Impact

- **Test 代码**：`src/tests/service/test_view_runtime_hardening.py` — 2 个测试函数的 dict 下标访问改为属性访问
- **前端**：`monitor-web/src/api/` 和 `monitor-web/src/pages/` — 逐模块对齐
- **无 API 破坏性变更**：仅是测试适配，不影响线上行为

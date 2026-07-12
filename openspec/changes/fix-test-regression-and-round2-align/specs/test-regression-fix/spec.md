# Test Regression Fix

## Purpose

修复 `test_view_runtime_hardening.py` 中因 View 创建 API 响应从 dict 改为 Pydantic `ViewResponse` 模型导致的 2 个测试回归。

## ADDED Requirements

### Requirement: Tests access ViewResponse via attribute instead of dict subscript

`test_create_view_commits_view_and_streaming_state` 和 `test_create_view_warns_when_raw_streams_are_unavailable` SHALL 使用属性访问（`.id`, `.warnings`）而非 dict 下标（`["view"]["id"]`, `["warnings"]`）来访问 `ViewResponse` 字段。

#### Scenario: POST /views response is flat ViewResponse

- **WHEN** 测试通过 `client.post("/api/v1/views/", ...)` 创建视图
- **THEN** `response.json()["id"]` SHALL 返回视图 ID（不再嵌套在 `["view"]` 下）
- **AND** `response.json()["warnings"]` SHALL 返回警告列表

#### Scenario: create_view() returns ViewResponse with attribute access

- **WHEN** 测试直接调用 `view_task.create_view(db, audio_id=..., video_id=...)`
- **THEN** 返回值 SHALL 是 `ViewResponse` 实例
- **AND** `result.warnings[-1]` SHALL 访问最后一个警告消息（不再使用 `result["warnings"][-1]`）

### Requirement: All tests in test_view_runtime_hardening.py pass

`test_view_runtime_hardening.py` 中的全部 4 个测试 SHALL 在 `pytest` 中通过。

#### Scenario: Full test suite passes

- **WHEN** 运行 `pytest src/tests/service/test_view_runtime_hardening.py`
- **THEN** 所有测试通过，无 KeyError 或 TypeError

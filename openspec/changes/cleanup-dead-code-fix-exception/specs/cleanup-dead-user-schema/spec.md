# Cleanup Dead User Schema

## Purpose

删除 `schema/http/user.py` —— 该文件的 `UserCreate` 和 `UserResponse` 从未被任何 router 使用，实际 API 使用 `auth_schema.py` 的版本。

## ADDED Requirements

### Requirement: Dead code removal

`schema/http/user.py` SHALL 被删除。项目中的任何代码 SHALL NOT 导入 `src.schema.http.user`。

#### Scenario: No import of user.py exists

- **WHEN** 搜索全项目 `from src.schema.http.user` 或 `import.*user`
- **THEN** 无任何匹配结果

#### Scenario: Test suite passes after deletion

- **WHEN** 删除 `user.py` 后运行 `pytest src/tests/api/`
- **THEN** 全部测试通过，无 import error

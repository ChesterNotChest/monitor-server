## ADDED Requirements

### Requirement: update — 更新记录
系统 SHALL 提供 `update(id: int, **kwargs) -> T | None` 方法，按主键查找记录，更新传入的字段并 flush。仅更新 kwargs 中非 None 的字段。返回更新后的模型实例，记录不存在则返回 `None`。

#### Scenario: 更新存在的记录
- **WHEN** 调用 `repo.update(1, name="新名称")` 且记录存在
- **THEN** 该记录的 `name` 字段更新为"新名称"，flush 后返回模型实例

#### Scenario: 更新不存在的记录
- **WHEN** 调用 `repo.update(999, name="新名称")` 且记录不存在
- **THEN** 返回 `None`，无数据库操作

#### Scenario: 部分字段更新
- **WHEN** 调用 `repo.update(1, avatar_path="/new/path.png")` 且记录存在
- **THEN** 仅 `avatar_path` 字段更新，其他字段不变

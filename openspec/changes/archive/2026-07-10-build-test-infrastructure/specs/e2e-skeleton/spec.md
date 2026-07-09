## ADDED Requirements

### Requirement: E2E 测试骨架
系统 SHALL 创建 `tests/e2e/` 目录骨架，包含 `_test.md` 说明文档和 `conftest.py`。

#### Scenario: E2E 测试目录就绪
- **WHEN** 开发者查看 `tests/e2e/`
- **THEN** 存在 `_test.md`（说明 E2E 的用途和运行方式）和 `conftest.py`（E2E 专用 fixtures）

### Requirement: E2E 说明文档
`_test.md` SHALL 说明 E2E 测试的运行方式（需要启动完整服务）、覆盖场景（完整 HTTP 请求链路）以及与冒烟/集成测试的区别。

#### Scenario: 理解 E2E 测试范围
- **WHEN** 阅读 `tests/e2e/_test.md`
- **THEN** 明确 E2E 测试何时使用、如何运行、依赖哪些外部服务

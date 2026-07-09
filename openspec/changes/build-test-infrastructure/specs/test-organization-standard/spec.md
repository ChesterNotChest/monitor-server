## ADDED Requirements

### Requirement: 测试目录镜像源码结构
系统 SHALL 要求 `tests/` 目录结构镜像 `src/` 包结构。每个源码包在 tests 下有对应的同名目录。

#### Scenario: 为 repository 包创建测试目录
- **WHEN** 开发者为 `src/repository/` 编写测试
- **THEN** 测试文件必须放置在 `tests/repository/` 下

#### Scenario: 为子模块创建测试目录
- **WHEN** 开发者为 `src/service/video_module/` 编写测试
- **THEN** 测试文件必须放置在 `tests/service/video_module/` 下

### Requirement: 每包维护 _test.md 说明文档
系统 SHALL 要求每个测试目录维护 `_test.md` 文件，简要记录覆盖范围和注意事项。

#### Scenario: 查看某包的测试说明
- **WHEN** 浏览 `tests/repository/_test.md`
- **THEN** 该文件说明本目录测试覆盖了哪些 repo 类、有哪些集成测试

### Requirement: 多模块测试归入主模块
系统 SHALL 规定涉及多个模块的测试用例归入被测试主模块的 test 目录。

#### Scenario: 多 Repo 协作集成测试
- **WHEN** 测试涉及 NodeRepo + VideoDeviceRepo + MonitorViewRepo 的协作流程
- **THEN** 该测试文件放置在 `tests/repository/test_integration.py`（因为主要逻辑在 repository 层）

### Requirement: E2E 测试统一归入 e2e 包
系统 SHALL 规定所有端到端测试统一放置在 `tests/e2e/` 目录下，不与任何业务模块耦合。

#### Scenario: 新增端到端测试
- **WHEN** 开发者编写完整的 HTTP 请求→数据库→响应的端到端测试
- **THEN** 该测试文件必须放置在 `tests/e2e/` 下

### Requirement: pytest 命名约定
系统 SHALL 要求所有测试文件遵循 pytest 命名约定：冒烟/单元测试使用 `test_*.py`，集成测试使用 `test_integration*.py`，说明文档使用 `_test.md`。

#### Scenario: pytest 自动发现
- **WHEN** 运行 `pytest tests/`
- **THEN** 自动发现所有 `test_*.py` 文件，跳过 `_test.md` 和 `__init__.py`

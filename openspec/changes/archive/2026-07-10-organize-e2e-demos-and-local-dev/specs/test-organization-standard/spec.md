## MODIFIED Requirements

### Requirement: 测试文件命名约束
文件名以 `test_` 为前缀的 Python 文件 SHALL 包含至少一个 `def test_*` 函数。不含测试函数的演示脚本和手动验证工具 SHALL 放置在 `tools/` 目录，命名为 `<name>_demo.py`。

#### Scenario: test_ 前缀但无测试函数
- **WHEN** `src/tests/` 下存在 `test_xxx.py` 文件但不含 `def test_*` 函数
- **THEN** 视为违规，应移至 `tools/` 或重命名去掉 `test_` 前缀

#### Scenario: Demo 脚本正确位置
- **WHEN** 开发者在 `tools/` 下创建 `live_camera_demo.py`
- **THEN** 不被 pytest 收集，手动 `python tools/live_camera_demo.py` 运行

### Requirement: e2e 目录规范
`src/tests/e2e/` 目录 SHALL 仅包含端到端测试文件（含 `def test_*`）和 `conftest.py`。禁止放置文档草稿（`_test.md` 等）和非测试脚本。

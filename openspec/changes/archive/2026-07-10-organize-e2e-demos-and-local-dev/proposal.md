## Why

1. **Demo scripts pollute e2e**: `test_live_camera.py` 和 `test_yamnet_live.py` 是无 `def test_*` 的手动脚本，以 `test_` 前缀放在 `e2e/` 下，每次 pytest 收集都浪费 3+ 秒，且误导开发者以为遗漏了测试。`_test.md` 是过期的计划文档。

2. **无本地联调范式**: Part A/B/C 的视觉（YOLO+标注+围栏+VLC）和听觉（YAMNet+EventBus）验证都依赖 Node 推流。当前 README 有 E2E 验证步骤但散落在多处，没有统一的 "本地联调 = Node 充当拉流工具 + Server 处理" 的固定范式。ls2 的 `test_live_camera.py` 就是这种需要的产物——但没有文档引导，开发者不知道它存在。

## What Changes

- 将 `test_live_camera.py` → `tools/live_camera_demo.py`，`test_yamnet_live.py` → `tools/yamnet_live_demo.py`
- 删除 `e2e/_test.md`（过期的计划文档）
- 更新 `test-organization-standard` spec：新增规则——`test_` 前缀文件必须含 `def test_*` 函数；demo/脚本放 `tools/`
- 新增 spec `local-dev-e2e-paradigm`：定义本地联调固定范式——Node 作为统一拉流源，127.0.0.1 配置，启动顺序，验证步骤

## Capabilities

### New Capabilities
- `local-dev-e2e-paradigm`: 本地开发联调范式——Node 充当摄像头/麦克风 → Server AI 处理 → VLC/OBS 播放标注流。包含固定配置、启动顺序、验收 checklist。

### Modified Capabilities
- `test-organization-standard`: 新增 `test_` 前缀命名约束，demo 脚本归属 `tools/`

## Impact

- **文件移动**: `e2e/test_live_camera.py` → `tools/live_camera_demo.py`，`e2e/test_yamnet_live.py` → `tools/yamnet_live_demo.py`
- **文件删除**: `e2e/_test.md`
- **Spec 更新**: `test-organization-standard` 补命名规则
- **Spec 新增**: `local-dev-e2e-paradigm`
- **README 修正**: Server README 中 `STREAM_DEBUG`（Node 已改名为 `RTMP_DEBUG`）→ `RTMP_DEBUG`

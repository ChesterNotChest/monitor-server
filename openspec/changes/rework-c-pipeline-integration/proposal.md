## Why

Part C 的 AlertEngine（告警引擎）和 YamnetRunner（音频分类）代码逻辑正确、EventBus 连接正确，但未被挂入 Part A 的管线生命周期。`vision_task.py` 已有 `start_pipeline()`/`stop_pipeline()` 入口，但内部只创建 AIPipeline，没有启动 C 模块。导致告警引擎和 YAMNet 永远不会运行。

## What Changes

- `vision_task.py` 的 `start_pipeline()` 追加：创建 AlertEngine → `await alert.start()`；有 audio_id 时创建 YamnetRunner → `asyncio.create_task(yamnet.run())`
- `vision_task.py` 的 `stop_pipeline()` 和 `stop_all()` 追加：停止 AlertEngine 和 YamnetRunner
- `vision_task.py` 或 `view_task.py`：找一个触发点调用 `start_pipeline(view_id, video_id, audio_id)`
- 清理 `src/tests/` 根目录下旧测试文件（test_alert_engine_unit.py、test_fence_event_types.py）

## Capabilities

### New Capabilities
_无_（纯集成修正，不引入新 capability）

### Modified Capabilities
_无_（不改变 spec 级行为）

## Impact

- 修改文件：`src/service/vision_task.py`（主要改动）、`src/service/view_task.py` 或 `src/app.py`（触发点）
- 删除文件：`src/tests/test_alert_engine_unit.py`、`src/tests/test_fence_event_types.py`

## Context

Part A 的 `vision_task.py` 已有完整管线生命周期：

```python
# vision_task.py 当前状态
_active_pipelines: dict[int, AIPipeline] = {}

async def start_pipeline(view_id, video_id, audio_id=None):
    pipeline = AIPipeline()
    if not await pipeline.start(view_id, video_id, audio_id):
        return False
    _active_pipelines[view_id] = pipeline
    return True

async def stop_pipeline(view_id):
    pipeline = _active_pipelines.pop(view_id, None)
    if pipeline:
        await pipeline.stop()
```

Part C 的 `AlertEngine` 和 `YamnetRunner` 独立存在但从未被启动。需要将它们注入管线生命周期。

## Changes

### 1. vision_task.py — 启动时创建 C 模块

```python
from src.service.alert_module.engine import AlertEngine
from src.service.audio_module.audio_yamnet import YamnetRunner

_alert_engines: dict[int, AlertEngine] = {}
_yamnet_runners: dict[int, YamnetRunner] = {}

async def start_pipeline(view_id, video_id, audio_id=None):
    # (existing AIPipeline logic)
    pipeline = AIPipeline()
    if not await pipeline.start(view_id, video_id, audio_id):
        return False
    _active_pipelines[view_id] = pipeline

    # 启动告警引擎
    alert = AlertEngine(view_id)
    await alert.start()
    _alert_engines[view_id] = alert

    # 有音频设备时启动 YAMNet
    if audio_id is not None:
        yamnet = YamnetRunner(view_id, audio_id)
        asyncio.create_task(yamnet.run())
        _yamnet_runners[view_id] = yamnet

    return True
```

### 2. vision_task.py — 停止时清理 C 模块

```python
async def stop_pipeline(view_id):
    # 停止 YAMNet
    yamnet = _yamnet_runners.pop(view_id, None)
    if yamnet:
        await yamnet.stop()
    # 停止 AlertEngine
    alert = _alert_engines.pop(view_id, None)
    if alert:
        await alert.stop()
    # (existing pipeline stop)
    pipeline = _active_pipelines.pop(view_id, None)
    if pipeline:
        await pipeline.stop()
```

`stop_all()` 遍历 `list(_active_pipelines.keys())` 调 `stop_pipeline`，自动覆盖 C 模块清理。

### 3. 触发点 — View 创建时启动管线

`view_task.py` 的 `create_view` 是自然触发点：View 创建成功 → 启动管线。

```python
# view_task.py create_view() 末尾追加
import asyncio
from src.service.vision_task import start_pipeline
try:
    loop = asyncio.get_running_loop()
    loop.create_task(start_pipeline(view.id, video_id, audio_id))
except RuntimeError:
    asyncio.run(start_pipeline(view.id, video_id, audio_id))
```

### 4. 清理旧测试文件

删除 `src/tests/test_alert_engine_unit.py` 和 `src/tests/test_fence_event_types.py`。正确版本在 `tests/service/` 和 `tests/api/` 下。

## Risks

- **asyncio.create_task 泄漏**：YamnetRunner 的 task 如果异常退出不会被自动清理。`stop_pipeline` 中调 `yamnet.stop()` 会取消 task。`stop_all` 遍历所有 view_id 确保 Server 关闭时全部清理。
- **重复启动**：`start_pipeline` 已有去重检查（`view_id in _active_pipelines`），C 模块跟随此逻辑。

## 1. 管线启停 — vision_task.py

- [ ] 1.1 导入 `AlertEngine` 和 `YamnetRunner`
- [ ] 1.2 新增 `_alert_engines: dict[int, AlertEngine]` 和 `_yamnet_runners: dict[int, YamnetRunner]` 全局字典
- [ ] 1.3 `start_pipeline()` 中 AIPipeline 启动成功后创建并启动 AlertEngine；有 audio_id 时创建 YamnetRunner 并用 `asyncio.create_task` 启动
- [ ] 1.4 `stop_pipeline()` 中先停 YamnetRunner → AlertEngine → 再 AIPipeline
- [ ] 1.5 `stop_all()` 确认覆盖所有模块清理

## 2. 触发点 — View 创建时启动管线

- [ ] 2.1 `view_task.py` 的 `create_view()` 末尾调用 `vision_task.start_pipeline(view_id, video_id, audio_id)`

## 3. 清理旧测试文件

- [ ] 3.1 删除 `src/tests/test_alert_engine_unit.py`
- [ ] 3.2 删除 `src/tests/test_fence_event_types.py`

## 4. 验证

- [ ] 4.1 全量 pytest 零失败（排除已知 cv2/numpy 依赖问题）
- [ ] 4.2 单个 View 启停循环 10 次，asyncio task 无泄漏
- [ ] 4.3 日志验证：启动时出现 "AlertEngine started" + YAMNet 模型加载日志

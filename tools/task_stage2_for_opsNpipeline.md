# Stage 2 任务清单 — 运维 + 管线收尾

**接手范围**: `E:/AI/monitor-server`（monitor-server + monitor-node 两侧）
**基准**: Merge ls2→chester 后，245 passed

---

## 一、Playbook 验证（优先）

merge 后全链路确认可用。

- [ ] 1.1 双靶子启动（:1935 rtmp_server + :1936 rtmp_debug_server）
- [ ] 1.2 Node 启动（libx264 drawtext 烧时间戳）
- [ ] 1.3 Server 启动（`DEBUG_WEB_STREAM=true YOLO_DEVICE=0 APP_DEBUG=false PORT=8002`）
- [ ] 1.4 创建 View 1 → VLC 播放 `rtmp://127.0.0.1:1936/view/1`
- [ ] 1.5 确认：15fps 稳推、Person ID N 标注正常、诶对了，playbook右下角有 Node 时间戳、延迟稳定不增长
- [ ] 1.6 确认 obs 日志输出正常：`[obs] loop FPS / push FPS / frame_age`

## 二、FrameReader 鲁棒性修复

当前 `_run_loop` 遇到 `FrameReaderState.ERROR` 直接 `break` 管线永久死亡。改为重试循环。

- [ ] 2.1 `_run_loop` 中 `FrameReader.ERROR` 时不再 break，改为尝试重新 `open()` 拉流（指数退避，最多 N 次）
- [ ] 2.2 重试日志：`FrameReader ERROR, retrying in Xs (attempt N/M)`
- [ ] 2.3 验证：Node 晚启动、Node 短暂断联后管线自动恢复

## 三、标注信息补全

当前只显示 `Person ID N`。`_enrich_detection_labels` 已预留 face/action/fence 拼接逻辑，
恢复对应模块后自然补齐。

- [ ] 3.0 恢复 face recognizer 后：`Person ID N Face: 张三`
- [ ] 3.0 恢复 SlowFast 后：`Person ID N Action: running`
- [ ] 3.0 恢复 Fence 后：`Person ID N Fence: zone-A`
- [ ] 3.0 全部恢复后：`Person ID 3 Face: 张三 Action: running Fence: zone-A`

## 四、人脸识别恢复

### 4.1 代码恢复

- [ ] 4.1.1 `video_ai_processor.py`：恢复 `face_recognizer.recognize_and_publish()` 调用
- [ ] 4.1.2 `video_ai_processor.py`：恢复 `slowfast_runner.enqueue_and_publish()` 调用

### 4.2 引导测试（Swagger 上传头像）

前提：dlib API 兼容性已在 ls2 中修复，但需确认本机 dlib 版本。

- [ ] 4.2.1 `POST /api/v1/named-persons/` 创建人物 → 记下返回的 `id`
- [ ] 4.2.2 `POST /api/v1/named-persons/{id}/avatar` 上传头像（multipart form-data，字段名 `file`）
- [ ] 4.2.3 创建 View → VLC 观察标注框是否显示 `Person ID N Face: {name}`

## 五、音频合流缺口

当前 AI 管线为 video-only。Audio 流需要合入最终流。

**问题**：pipe:0 + RTMP 音频双输入在同一个 ffmpeg 中死锁。纯 RTMP→RTMP 方式已验证可工作（两阶段方案），但中间流增加延迟。

- [ ] 5.1 方案选择：SRS 合流（运维域）vs Server 侧两阶段合流（自己可控）
- [ ] 5.2 若选 Server 侧：需要解决中间流延迟问题（anullsrc 占位 + 后续热切换真实音频？）
- [ ] 5.3 无论选哪种，记下当前缺口便于后续接手

## 六、已知搁置项

| 项目 | 状态 | 原因 |
|------|------|------|
| Node ~20s 延迟 | 搁置 | Node 采集管道固有延迟（dshow+h264_mf），理论可消但非紧急 |
| 时间戳由 Server 推算 | 搁置 | Server 无法获知采集时刻，当前用 Node drawtext 烧录 |
| GOP cache 快进 | 已缓解 | `gop_cache: false` + 全清重启基本消除 |
| async push（队列+drain task） | 搁置 | 当前同步 push 足够稳，async 化留到后面优化 |

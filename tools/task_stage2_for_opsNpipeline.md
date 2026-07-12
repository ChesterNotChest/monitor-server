# Stage 2 任务清单 — 运维 + 管线收尾

**接手范围**: `E:/AI/monitor-server`（monitor-server + monitor-node 两侧）
**基准**: Merge ls2→chester 后，245 passed

---

## 一、Playbook 验证 ✅ (2026-07-11)

merge 后全链路确认可用。

- [x] 1.1 双靶子启动（:1935 rtmp_server + :1936 rtmp_debug_server）
- [x] 1.2 Node 启动（h264_mf + drawtext 烧时间戳）
- [x] 1.3 Server 启动（`DEBUG_WEB_STREAM=true YOLO_DEVICE=0 APP_DEBUG=false PORT=8002`）
- [x] 1.4 创建 View 1 → VLC 播放 `rtmp://127.0.0.1:1936/view/1`
- [x] 1.5 确认：r_frame_rate=10/1、Person ID N 标注正常、右下角有 Node 时间戳
- [x] 1.6 确认 obs 日志输出正常：`[obs] FPS=10.0 | r=0 y=16 pipe=16 frame_age=2ms`

### 基线 v3 (2026-07-11 最终)

```
FPS_TARGET=17  (Node 采集上限 17fps，Server 17fps 处理，全链路对齐)
h264_nvenc -preset p1 -zerolatency 1
Node: -framerate 17 -fflags nobuffer -rtbufsize 4M -b:v 1M
obs:  r=0ms  y=16ms  hk=0ms  pipe=16ms  push=17fps  帧率对齐
标注: Person ID N + Face: Stranger + Sitting (枚举 16 类)
可视化: 浅绿虚线框 = SlowFast padded crop (+30%)
```

## 二、FrameReader 鲁棒性修复 ✅ (2026-07-11)

当前 `_run_loop` 遇到 `FrameReaderState.ERROR` 直接 `break` 管线永久死亡。改为重试循环。

- [x] 2.1 `_run_loop` 中 `FrameReader.ERROR` 时不再 break，调用 `_reopen_reader()`（指数退避 2s→60s，最多 10 次）
- [x] 2.2 重试日志：`FrameReader reopen attempt N/10 in X.Xs ...` → `FrameReader reopened successfully (attempt N)`
- [x] 2.3 验证：:1935 kill→restart 后管线 attempt 4 自动恢复，obs 显示 `FPS=10.0 | r=0` 稳态
- [x] 附带修复：`:1935 rtmp_server/index.js` 的 `gop_cache: true→false`（长 GOP 导致新客户端 30s 超时）
- [x] 附带修复：`start()` 中首次 `_reader.open()` 失败不再阻止管线启动，交由 `_run_loop` 重试
- [x] 附带修复：`FrameReader._handle_read_failure()` 删除 `_last_url` 死代码；新增 `reset_error()`
- [x] 245 passed

## 三、标注信息补全 ✅ (2026-07-11)

- [x] Face: Stranger 显示正常（dlib + C2 持久缓存 + 增量更新）
- [x] Action: Sitting/Standing/Waving 等显示正常（SlowFast AVA+Kinetics 双模型 + 线程池）
- [x] 枚举同步：`constants.py` 16 类对齐 `seed_data.py` ACTION_NAMES
- [x] 可视化：浅绿虚线框标注 SlowFast padded crop 区域
- [ ] Fence：逻辑就绪，待配置围栏区域即可激活
- [x] 事件总线 Bug：workaround 绕过，`video_ai_processor.py` 直接更新全局 dict
- [x] 250 passed

## 四、人脸识别恢复 ⏳ (代码已恢复，待引导测试)

### 4.1 代码恢复 ✅

- [x] 4.1.1 `video_ai_processor.py`：已恢复 `face_recognizer.recognize_and_publish()` 
- [x] 4.1.2 `video_ai_processor.py`：已恢复 `slowfast_runner.enqueue_and_publish()`
- [x] C2 人脸缓存：同 track_id 只识别一次，后续帧零开销
- [x] Face 标签增量更新（不清空已有标签）
- [x] SlowFast 线程池：推理不阻塞主循环

### 4.2 引导测试（待执行）

- [ ] 4.2.1 `POST /api/v1/persons/` 创建人物
- [ ] 4.2.2 `POST /api/v1/persons/{id}/avatar` 上传头像
- [ ] 4.2.3 重启管线 → VLC 观察 `Person ID N Face: {name}`

## 五、音频合流缺口

当前 AI 管线为 video-only。Audio 流需要合入最终流。

**问题**：pipe:0 + RTMP 音频双输入在同一个 ffmpeg 中死锁。纯 RTMP→RTMP 方式已验证可工作（两阶段方案），但中间流增加延迟。

- [ ] 5.1 方案选择：SRS 合流（运维域）vs Server 侧两阶段合流（自己可控）
- [ ] 5.2 若选 Server 侧：需要解决中间流延迟问题（anullsrc 占位 + 后续热切换真实音频？）
- [ ] 5.3 无论选哪种，记下当前缺口便于后续接手

## 六、已知搁置项

| 项目 | 状态 | 原因 |
|------|------|------|
| Node 累积延迟 | 修复中 | 采集 30fps→17fps + nobuffer + 4M；待验证 |
| Fence 围栏标注 | 未测 | 代码就绪，需配置围栏区域后验证 |
| 时间戳嵌入 | 搁置 | §五音频合流前置，PTS/SEI 方案已讨论 |
| EventBus 订阅静默失败 | Workaround | `video_ai_processor.py` 直接更新全局 dict |
| PyAV 替代 subprocess | 搁置 | 按需，当前 ffmpeg pipe 足够稳 |

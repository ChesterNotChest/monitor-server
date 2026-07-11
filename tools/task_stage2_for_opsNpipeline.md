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

### 基线 v2 (2026-07-11 最终)

```
FPS_TARGET=30  (对齐摄像头 30fps 采集率)
h264_nvenc -preset p1 -zerolatency 1
obs:  r=0ms  y=16ms  pipe=16ms  push=29.2fps  稳定无振荡  画面实时
```

> **教训**：:1935 的 `gop_cache:true` 掩盖了真实帧率。GOP 批发出 burst 模式，
> 表观只有 ~10fps，误导判断为"Node 性能不足"。修成 `false` 后源帧即时到达，
> 30fps 真实速率暴露。FPS_TARGET 必须对齐采集帧率，否则就是慢动作。
>
> v1 基线 (FPS_TARGET=10) 因基于 gop_cache artifact 的误判，已废弃。

## 二、FrameReader 鲁棒性修复 ✅ (2026-07-11)

当前 `_run_loop` 遇到 `FrameReaderState.ERROR` 直接 `break` 管线永久死亡。改为重试循环。

- [x] 2.1 `_run_loop` 中 `FrameReader.ERROR` 时不再 break，调用 `_reopen_reader()`（指数退避 2s→60s，最多 10 次）
- [x] 2.2 重试日志：`FrameReader reopen attempt N/10 in X.Xs ...` → `FrameReader reopened successfully (attempt N)`
- [x] 2.3 验证：:1935 kill→restart 后管线 attempt 4 自动恢复，obs 显示 `FPS=10.0 | r=0` 稳态
- [x] 附带修复：`:1935 rtmp_server/index.js` 的 `gop_cache: true→false`（长 GOP 导致新客户端 30s 超时）
- [x] 附带修复：`start()` 中首次 `_reader.open()` 失败不再阻止管线启动，交由 `_run_loop` 重试
- [x] 附带修复：`FrameReader._handle_read_failure()` 删除 `_last_url` 死代码；新增 `reset_error()`
- [x] 245 passed

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
| GOP cache 快进 | 已修复 | :1935 + :1936 均 `gop_cache: false` |
| async push（队列+drain task） | 搁置 | 当前同步 push 足够稳，async 化留到后面优化 |
| EventBus 订阅静默失败 | Workaround | 模块级 `create_task(subscribe)` 有时不执行；`video_ai_processor.py` 直接更新全局 dict 绕过。详见 `vision_annotation.py:84-94` 注释 |

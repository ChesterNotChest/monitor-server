# Part B — 功能层

> **负责人**: ___
> **依赖**: Part A（模型、配置、Schema、Repository、Network 层）
> **并行策略**: 可用 mock repository + mock ConnectionRegistry 先行开发，Part A 完成后切换真实实现。

## 6. 清理旧占位文件

- [ ] 6.1 删除 `src/service/video_task.py`（已被 `view_task.py` 替代）
- [ ] 6.2 删除 `src/service/video_module/`（已被 `view_module/` 替代）

> **代码约定**：新建的占位文件 SHALL 在顶部包含中文 docstring 说明该模块的预期职责（如当前 `src/service/__init__.py` 的示例写法）。

## 7. Service 层 — Node Stream

- [ ] 7.1 创建 `src/service/node_stream_task.py` 门户函数：`handle_node_connected(db, node_id)` — 连接建立后记录日志、校验设备列表完整性。当前 Server 在握手响应中已直接推送已有设备，无需再做 LIST_DEVICES 交互。保留此函数作为后续 DEVICE_CHANGED 事件的入口点
- [ ] 7.2 创建 `src/service/node_stream_module/` 包（`__init__.py`、`device_sync.py`）
- [ ] 7.3 `device_sync.py` 实现 `sync_devices(db, node_id, videos, audios)`：遍历视频/音频列表，已存在的跳过（基于 (node_id, name) 联合唯一），不存在的插入 DB。注：当前阶段此函数保留备用——连接握手时 Server 直接查询已有设备返回，不经过 sync；后续 DEVICE_CHANGED 事件实现时会用到

## 8. Service 层 — Node Task（轻量包装）

- [ ] 8.1 创建 `src/service/node_task.py` 门户函数：`list_nodes(db)`→ `NodeRepo(db).all()`、`get_node(db, node_id)` → `NodeRepo(db).get(node_id)`、`list_videos_by_node(db, node_id)` → `VideoDeviceRepo(db).by_node(node_id)`、`list_audios_by_node(db, node_id)` → `AudioDeviceRepo(db).by_node(node_id)`

> 这些是简单只读透传，但为保持分层一致性和可读性，Router 不直接调 Repository。

## 9. Service 层 — View

- [ ] 9.1 创建 `src/service/view_task.py` 门户函数：`create_view(db, audio_id, video_id)`、`delete_view(db, view_id)`、`list_views(db)`、`get_view(db, view_id)`
- [ ] 9.2 创建 `src/service/view_module/` 包（`__init__.py`、`lifecycle.py`、`ffmpeg_manager.py`）
- [ ] 9.3 `lifecycle.py` 实现：
  - `get_ref_count(db, device_type, device_id)` — 调 `MonitorViewRepo(db).count_by_video_id()` / `count_by_audio_id()`
  - `check_and_start_stream(db, device_type, device_id)` — 通过 `VideoDeviceRepo(db).get()` / `AudioDeviceRepo(db).get()` 查设备获取 `node_id`；查引用计数（=0 表示无 View 在用）→ 0 则发 `UPDATE_STREAM` + `update_streaming(id, True)` → 返回 True；>0 → 返回 False
  - `check_and_stop_stream(db, device_type, device_id)` — 删除后查引用计数 → 0 则发 `UPDATE_STREAM` + `update_streaming(id, False)` → 返回 True；>0 → 返回 False
- [ ] 9.4 `ffmpeg_manager.py` 实现：
  - `start_merge(view_id, video_id, audio_id)` — 通过 `VideoDeviceRepo(db).get(video_id)` / `AudioDeviceRepo(db).get(audio_id)` 查设备名称，构建 RTMP 拉流地址，推流目标由 `pusher.build_push_url(view_id)` 决定（生产→SRS，debug→本地靶子 `rtmp://127.0.0.1:1936/view/{view_id}`），`asyncio.create_subprocess_exec` 启动 FFmpeg
  - `stop_merge(view_id)` — SIGTERM 终止，失败仅记日志
  - `active_processes` 字典（`{view_id: subprocess}`）
  - `cleanup_all()` — atexit 注册，遍历终止所有

`create_view` 内部逻辑（关键函数）：
1. 验证设备存在：`VideoDeviceRepo(db).get(video_id)` / `AudioDeviceRepo(db).get(audio_id)` — 任一不存在返回 404
2. `warnings = []`
3. `check_and_start_stream("video", video_id)` — False 则 warnings.append(...)
4. `check_and_start_stream("audio", audio_id)` — False 则 warnings.append(...)
5. `view = MonitorViewRepo(db).create(audio_id=audio_id, video_id=video_id)`
6. `ffmpeg_manager.start_merge(view.id, video_id, audio_id)`
7. `urls = pusher.build_play_urls(view.id)`
8. 返回 ViewResponse（含 flv_url、webrtc_url、warnings）

`delete_view` 内部逻辑（DB 优先，FFmpeg 后杀）：
1. `view = MonitorViewRepo(db).get(view_id)` — 不存在返回 404
2. `MonitorViewRepo(db).delete(view_id)` — **先删 DB（事务保护）**
3. `ffmpeg_manager.stop_merge(view_id)` — 成功后再杀 FFmpeg，失败仅记日志
4. `check_and_stop_stream("video", view.video_id)`
5. `check_and_stop_stream("audio", view.audio_id)`

## 10. API 路由

- [ ] 10.1 创建 `src/network/api/node_router.py`：`GET /api/v1/nodes`（调 `node_task.list_nodes`）、`GET /api/v1/nodes/{node_id}/videos`（调 `node_task.list_videos_by_node`）、`GET /api/v1/nodes/{node_id}/audios`（调 `node_task.list_audios_by_node`）
- [ ] 10.2 创建 `src/network/api/view_router.py`：`POST /api/v1/views`、`GET /api/v1/views`、`GET /api/v1/views/{view_id}`、`DELETE /api/v1/views/{view_id}`
- [ ] 10.3 创建 `src/network/api/__init__.py` 汇总所有 Router

## 11. DEBUG_WEB_STREAM 本地靶子

- [ ] 11.1 创建 `tools/rtmp_debug_server.js`：基于 node-media-server，监听 `rtmp://127.0.0.1:1936/live`，接受 Server 推来的合并 View 流，可供 OBS 拉流测试。复用 Node 项目 `rtmp_server/index.js` 的模式，改端口避免与 Node 的 STREAM_DEBUG 用 `1935` 冲突
- [ ] 11.2 `ffmpeg_manager.py` 的 debug 模式：`DEBUG_WEB_STREAM=true` 时，`start_merge` 推流到 `rtmp://127.0.0.1:1936/view/{view_id}`；`stop_merge` 正常终止；`build_play_urls` 返回 `rtmp://127.0.0.1:1936/view/{view_id}` 供 OBS 使用

## 12. 包初始化更新

- [ ] 12.1 更新 `src/service/__init__.py`：导入 `node_task`、`node_stream_task`、`view_task`

## 13. App 集成

- [ ] 14.1 更新 `src/app.py`：导入 `src/network/api/` 的汇总 Router 并 `include_router`、导入 `src/network/wss/node_handler.py` 的 WebSocket 端点并注册、注册 `atexit` 清理回调（终止所有 FFmpeg 子进程）
- [ ] 14.2 更新 `src/models/__init__.py` 确保 `Base.metadata.create_all` 覆盖所有新字段 + 联合唯一约束（与 Part A 1.5 协调）
- [ ] 14.3 更新 README.md 目录结构说明，反映 `src/network/` 三层架构

## 14. 测试

### 14.1 模型层

- [ ] 14.1.1 创建 Node → 验证 `is_connected` 默认 false、`last_seen` 默认 NULL
- [ ] 14.1.2 创建 VideoDevice → 验证 `streaming` 默认 false
- [ ] 14.1.3 创建 AudioDevice → 验证 `streaming` 默认 false
- [ ] 14.1.4 同一 node 下重名 VideoDevice → 验证联合唯一约束拒绝
- [ ] 14.1.5 不同 node 下同名 VideoDevice → 验证成功插入（联合唯一不跨 node）
- [ ] 14.1.6 MonitorView 插入时 `audio_id=NULL` → 验证 non-nullable 约束拒绝

### 14.2 Repository 层 — 扩展方法测试

> 基础 CRUD 测试已存在（`tests/repository/test_node_repo.py` 等 14 个文件）。本节仅测试本次新增的方法。

- [ ] 14.2.1 `NodeRepo(db).update_connection_status(node_id, True, now)` → 验证 `is_connected` / `last_seen` 更新
- [ ] 14.2.2 `NodeRepo(db).reset_device_streaming_by_node(node_id)` → 验证该 Node 下所有设备 `streaming=false`
- [ ] 14.2.3 `VideoDeviceRepo(db).upsert(node_id, "cam0")` 新设备 → INSERT 成功
- [ ] 14.2.4 `VideoDeviceRepo(db).upsert(node_id, "cam0")` 已有设备（同 node_id + name）→ 不重复 INSERT
- [ ] 14.2.5 `MonitorViewRepo(db).count_by_video_id(video_id)` → 计数正确（含多 View 共享场景）
- [ ] 14.2.6 `MonitorViewRepo(db).count_by_audio_id(audio_id)` → 计数正确

### 14.3 Schema 层

- [ ] 14.3.1 `ConnectRequest(token="abc")` → 序列化验证通过
- [ ] 14.3.2 `ConnectResponse` 反序列化 → 正确解析 `session_token`、`videos`、`audios` 字段
- [ ] 14.3.3 `ViewCreateRequest(audio_id=1, video_id=1)` → 校验通过
- [ ] 14.3.4 `ViewCreateRequest(audio_id=None, video_id=1)` → 校验失败
- [ ] 14.3.5 `UpdateStreamRequest` 序列化 → JSON 格式符合 `{command, device_type, device_id, enable}`

### 14.4 ConnectionRegistry + 断连级联

- [ ] 14.4.1 `register(node_id, mock_ws)` → `get(node_id)` 返回 mock_ws
- [ ] 14.4.2 `unregister(node_id)` → `get(node_id)` 返回 None
- [ ] 14.4.3 `is_online` 正确反映注册状态
- [ ] 14.4.4 `send_command` 目标离线 → 抛出 NodeOfflineError
- [ ] 14.4.5 `send_command` 成功 → 发送 JSON 并返回解析后的 Response
- [ ] 14.4.6 Node 断连 → 验证级联清理：`is_connected=false` + 该 Node 下所有设备 `streaming=false`

### 14.5 引用计数逻辑 (lifecycle)

- [ ] 14.5.1 `check_and_start_stream` 计数=0 → 调 send_command + update_streaming(True)，返回 True
- [ ] 14.5.2 `check_and_start_stream` 计数>0 → 不调 send_command，返回 False
- [ ] 14.5.3 `check_and_stop_stream` 计数=0 → 调 send_command + update_streaming(False)，返回 True
- [ ] 14.5.4 `check_and_stop_stream` 计数>0 → 不调 send_command，返回 False

### 14.6 集成测试（端到端，需 mock WSS + SRS）

- [ ] 14.6.1 `POST /views`（新设备）→ 200, warnings=[], srs_urls 非空
- [ ] 14.6.2 `POST /views`（流已被占用）→ 200, warnings 非空
- [ ] 14.6.3 `POST /views`（设备不存在）→ 404
- [ ] 14.6.4 `DELETE /views`（最后一个引用）→ 200, DB 记录已删除, FFmpeg 进程已终止
- [ ] 14.6.5 `DELETE /views`（仍有其他 View 引用同一设备）→ 200, 不发送 UPDATE_STREAM=false
- [ ] 14.6.6 `GET /nodes` → 返回列表含 `is_connected`、`last_seen` 字段

---

## Mock 开发指南（并行时使用）

如果 Part A 尚未完成，可用以下 mock 先行开发：

```python
# 示例：mock repository（匹配现有 BaseRepo 类模式）
class MockNodeRepo:
    def all(self): pass  # 实际由 pytest fixture 提供真实 SQLite 内存库
    def get(self, id): pass
    def by_token(self, token): pass
    def update_connection_status(self, node_id, is_connected, last_seen): pass
    def reset_device_streaming_by_node(self, node_id): pass

class MockVideoDeviceRepo:
    def get(self, id): pass
    def by_node(self, node_id): pass
    def upsert(self, node_id, name): pass
    def update_streaming(self, device_id, streaming): pass

class MockAudioDeviceRepo:
    # 同 VideoDeviceRepo 结构
    pass

class MockMonitorViewRepo:
    def create(self, **kw): pass
    def delete(self, id): pass
    def get(self, id): pass
    def count_by_video_id(self, video_id): return 0
    def count_by_audio_id(self, audio_id): return 0

class MockConnectionRegistry:
    def __init__(self):
        self._connections = {}
    def get(self, node_id):
        return self._connections.get(node_id)
    async def send_command(self, node_id, request):
        return type(request.__class__.__name__.replace("Request", "Response"))(
            success=True, message=None
        )
```

接口规范参见 `tasks-part-a.md` 末尾的契约表。切换真实实现时，只需改 import 路径即可。

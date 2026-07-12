## Context

e2e 目录目前混杂了三类内容：真实端到端测试（`test_recording_lifecycle.py`）、手动 demo 脚本（`test_live_camera.py`、`test_yamnet_live.py`）、文档草稿（`_test.md`）。后两类以 `test_` 前缀命名，导致 pytest 收集时浪费资源。需要分离。

此外 Part A/B/C 的视觉听觉验证都依赖 Node 推流，但当前缺少一个统一的本地联调范式。`tools/` 目录已有 `rtmp_debug_server.js`（Server 侧推流靶子），demo 脚本天然属于同一位置。

## Goals / Non-Goals

**Goals:**
- 清理 e2e 目录，保留真实测试
- 为 demo 脚本建立明确的 `tools/` 归处
- 定义本地联调的固定范式（配置、启动顺序、验收点）
- 更新 spec 防止同样问题复发

**Non-Goals:**
- 修改 demo 脚本的业务逻辑（只改名和移动）
- 实现新的测试框架

## Decisions

### Decision 1: tools/ 作为 demo 脚本的统一目录

`test_live_camera.py` → `tools/live_camera_demo.py`
`test_yamnet_live.py` → `tools/yamnet_live_demo.py`

**Rationale**: `tools/rtmp_debug_server.js` 已在此目录，该目录本就是开发辅助工具集。demo 脚本同样面向开发者手动执行，属于同类。

### Decision 2: 本地联调范式 = Node 推流 + Server 拉流处理

固定拓扑：
```
Camera/Mic → Node(FFmpeg 推流) → RTMP :1935 → Server(拉流+AI处理) → RTMP :1936 → VLC/OBS
(原始流)                          (标注流)
```

固定的两终端启动：
- Terminal 1 Node（推流）: `RTMP_DEBUG=true DEBUG_WSS=false SERVER_BASE_URL=127.0.0.1 python -m src.run`
- Terminal 2 Server（拉流处理）: `DEBUG_WEB_STREAM=true RTMP_DEBUG=true python -m src.run`

不需要 SRS、不需要 Docker。Node 就是统一的推流源，Server 就是统一的拉流处理端。

### Decision 3: 验收 checklist 风格

spec 中验收点用 checklist 形式，开发者逐条打勾：
- [ ] Node 启动，日志显示设备列表
- [ ] VLC 能打开 `rtmp://127.0.0.1:1935/live/{stream_name}` 看到原始画面
- [ ] Server 启动，日志显示 WSS 连接成功
- [ ] Swagger 能创建 View
- [ ] VLC 能打开 `rtmp://127.0.0.1:1936/view/{view_id}` 看到标注画面
- [ ] 标注画面有 YOLO 框 + 时间戳

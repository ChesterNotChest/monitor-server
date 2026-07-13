## Why

当前系统只能通过 Node 端 ffmpeg dshow 枚举本地摄像头/话筒作为设备源，无法接入外部 RTMP 流（如 IPC 摄像头、OBS 推流、第三方视频源）。调试和扩展场景受限。

## What Changes

- **虚拟 Node**：SEED 中预置一个常驻虚拟 Node，`is_connected` 始终为 false，不接受 WSS 连接，专门承载外部 RTMP 设备
- **自定义流 API**：`POST /nodes/{virtual_id}/devices/` 接口，允许向虚拟 Node 添加 video/audio 设备并指定 `stream_url`（RTMP 地址）。系统用 ffprobe 验证流可达性
- **View 音频可选**：`audio_id` 改为 nullable，创建 View 时可不选音频。无音频时 YAMNet 自动跳过
- **FrameReader 适配**：VideoDevice 新增 `stream_url` 字段，FrameReader 优先使用 `stream_url` 而非 `build_pull_url()`
- **前端支持**：View 创建设备选择器跨 Node 过滤，音频下拉增加"无"选项

## Capabilities

### New Capabilities
- `custom-stream-node`: 虚拟 Node + 外部 RTMP 流设备管理 + ffprobe 在线验证
- `optional-audio-view`: View 音频字段改为可选，无音频时自动关闭 YAMNet

### Modified Capabilities
- `view-management`: `audio_id` 约束从 NOT NULL → nullable
- `node-server-stream-naming`: FrameReader 增加 `stream_url` 优先路径

## Impact

- **修改文件**: `models/monitor_view.py`, `models/video_device.py`, `models/audio_device.py`, `seed.py`, `vision_task.py`, `vision_frame_reader.py`, `view_router.py`, 新增 `device_router.py` 的 stream 端点
- **不改**: Pipeline, AlertEngine, YAMNet 本身（已有 audio_id=None 的跳过逻辑）
- **风险**: 低。虚拟 Node 复用现有所有管线，只改变了设备来源通道

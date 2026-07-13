## Context

当前设备来源完全依赖 Node WSS 推送，创建 View 时 audio_id 强制 NOT NULL。需要开辟第二设备来源通道，同时允许纯视频 View。

## Goals / Non-Goals

**Goals:**
- SEED 中常驻一个虚拟 Node，不接受 WSS，专用于外部 RTMP 流
- 提供 API 向虚拟 Node 注册 RTMP video/audio 设备，ffprobe 验证在线
- View 创建时 audio 可选，不选则无 YAMNet
- VideoDevice 增加 `stream_url`，FrameReader 优先使用

**Non-Goals:**
- 不拆流、不转码
- 虚拟 Node 的流不要求 WSS 在线心跳
- 不修改 Node 端代码

## Decisions

### D1: 虚拟 Node 用 SEED 内置

```python
# seed.py
if not db.query(Node).filter(Node.name == "virtual").first():
    db.add(Node(name="virtual", is_connected=False))
    db.commit()
```

虚拟 Node 永远 `is_connected=False`，`node_handler.py` 不做 WSS 重连。

**替代方案**: API 动态创建 → 无必要，虚拟 Node 是基础设施，一条记录够用。

### D2: 设备流地址存 VideoDevice.stream_url

```python
class VideoDevice(Base):
    stream_url: Mapped[str | None] = mapped_column(nullable=True)
```

`stream_url` 非空时 FrameReader 直接 `cv2.VideoCapture(stream_url)`，跳过 `build_pull_url()`。

### D3: 流在线验证用 ffprobe

`POST /nodes/{id}/devices/` 创建设备前，ffprobe `rtmp://...` 验证流可达。超时 5s。不可达返回 400。不影响已创建的设备。

### D4: audio_id nullable

`MonitorView.audio_id` 改为 `nullable=True`。`start_pipeline` 中 `audio_id=None` 时不启动 YAMNet。

YAMNet 跳过逻辑已存在：`start_pipeline` 检查 `audio_id and audio_name`。

### D5: View 创建 API 适配

`POST /views/` body 中 `audio_id` 改为 optional。前端下拉增加"无音频"。

## Risks / Trade-offs

- **[R1] 虚拟 Node 离线显示** → UI 上虚拟 Node 永远离线。Mitigation: 前端特殊处理虚拟 Node 的状态显示
- **[R2] stream_url 无心跳** → 流中断时系统不感知，直到 FrameReader 报错重连。Mitigation: FrameReader 已有重连机制

## Migration Plan

1. DB migration: `audio_id` NOT NULL → nullable；VideoDevice 加 `stream_url`
2. SEED 加虚拟 Node
3. 新增设备注册 API
4. FrameReader 加 `stream_url` 优先路径
5. 前端适配

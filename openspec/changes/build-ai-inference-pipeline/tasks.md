# Tasks — 智能识别管线

> 已拆分为三份并行文件。

| 文件 | 负责人 | 依赖 | 任务数 |
|------|--------|------|--------|
| [tasks-a-foundation.md](tasks-a-foundation.md) | ___ | 无 | 36 |
| [tasks-b-video-ai.md](tasks-b-video-ai.md) | ___ | A（EventBus + Detection 格式） | 20 |
| [tasks-c-audio-alert.md](tasks-c-audio-alert.md) | ___ | A（EventBus 接口） | 28 |

**依赖拓扑：**

```
     ┌─────────────────┐
     │  A — 基础层      │
     │  模型/EventBus/  │
     │  帧管线/YOLO/    │
     │  标注合并/配置    │
     └───────┬─────────┘
             │ EventBus 接口 + Detection 格式
       ┌─────┴─────┐
       │           │
       ▼           ▼
┌──────┴──────┐ ┌──┴────────────┐
│ B — 视频 AI  │ │ C — 音频+告警 │
│ ByteTrack   │ │ YAMNet        │
│ 人脸识别     │ │ AlertEngine   │
│ SlowFast    │ │ Fence CRUD    │
│ 电子围栏     │ │ App 集成      │
└─────────────┘ └───────────────┘
```

**并行策略**：B/C 可用 Part A 的 interface mock 先行开发。Part A 完成后切换真实实现。

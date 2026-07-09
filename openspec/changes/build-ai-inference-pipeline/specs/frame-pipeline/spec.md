# Frame Pipeline

**Purpose:** OpenCV 从 SRS 拉取 RTMP 视频流，逐帧解码供 AI 管线消费。

## ADDED Requirements

### Requirement: OpenCV 拉流

系统 SHALL 使用 OpenCV `VideoCapture` 从 SRS 拉取 View 的 raw video RTMP 流。SHALL 支持断流重连——拉流中断时自动重试，重连成功恢复帧产出。每个 View SHALL 维护一个独立的 `VideoCapture` 实例。

#### Scenario: 正常拉流

- **WHEN** View `video_id=1` 的 raw RTMP 流在 SRS 上可用
- **THEN** `VideoCapture("rtmp://srs:1935/live/video_1")` 返回帧迭代器，fps 不低于源流帧率

#### Scenario: 断流重连

- **WHEN** RTMP 连接断开（SRS 重启或网络抖动）
- **THEN** 系统自动重试连接，指数退避 1s→60s，重连成功后恢复帧产出

### Requirement: 帧率控制

系统 SHALL 提供可配置的目标帧率（`FPS_TARGET`，默认 15）。若源流帧率高于目标，SHALL 跳帧（每 N 帧取 1）。若源流帧率低于目标，SHALL 等待源流产出。

#### Scenario: 跳帧

- **WHEN** `FPS_TARGET=10` 且源流 30fps
- **THEN** 每 3 帧取 1 帧送 AI 管线

### Requirement: Frame Pipeline 状态机

帧管线 SHALL 维护三态状态机：IDLE（未拉流）→ ACTIVE（正常产帧）→ ERROR（断流）。

#### Scenario: 状态转移

- **WHEN** 断流超过 3 次连续重连失败
- **THEN** 状态转为 ERROR，记录日志，继续尝试重连但不阻塞主循环

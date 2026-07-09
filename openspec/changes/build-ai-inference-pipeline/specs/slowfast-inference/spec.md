# SlowFast Inference

**Purpose:** 基于 ByteTrack per-person 帧队列 → SlowFast Kinetics + AVA 并行推理 → ActionType 枚举事件。

## ADDED Requirements

### Requirement: Per-person 帧队列

系统 SHALL 为每个 track_id 维护独立的帧队列（`collections.deque`，最大长度 32）。新帧到达时 append，队列满时 popleft（FIFO 丢旧帧）。队列满 32 帧时 SHALL 送 SlowFast 推理。

#### Scenario: 队列累积

- **WHEN** track_id=A 连续 32 帧出现在画面中
- **THEN** 队列满，送 SlowFast 推理，推理后清空队列

#### Scenario: FIFO 丢旧帧

- **WHEN** 队列已满 32 帧且新帧到达
- **THEN** popleft 最旧帧，append 新帧，保持队列长度 32

### Requirement: Kinetics 场景分类

系统 SHALL 使用 SlowFast R-50 Kinetics-400 预训练模型对 32 帧 clip 做场景级行为分类。SHALL 映射到 `ai-model-capability` spec 定义的 12 类 ActionType。

#### Scenario: 检测跌倒

- **WHEN** 32 帧 clip 中人物从站立变倒地且停留
- **THEN** 产出 `ActionType.FALLING (3)` 事件

### Requirement: AVA 人物动作检测

系统 SHALL 使用 SlowFast R-50 AVA 2.2 模型对同一 32 帧 clip 做人物级动作检测。吸烟（smoking）检测 SHALL 触发独立异常行为记录。

#### Scenario: 检测抽烟

- **WHEN** 32 帧 clip 中人物手持香烟靠近嘴部
- **THEN** 产出 smoking 检测框事件

### Requirement: SlowFast 状态机

SlowFast SHALL 维护 IDLE（无队列）→ ACTIVE（队列累积与推理）→ ERROR（模型加载失败）。队列满推理异常 SHALL 清空队列继续。

#### Scenario: 推理异常

- **WHEN** SlowFast 推理时 GPU/CPU 异常
- **THEN** 清空当前队列，记录日志，下一次队列满时重试

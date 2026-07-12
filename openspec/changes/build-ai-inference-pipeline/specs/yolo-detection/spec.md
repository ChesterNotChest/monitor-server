# YOLO Detection

**Purpose:** YOLO11n 目标检测——video 管线线性前置，产出 EntityType 枚举事件列表。

## ADDED Requirements

### Requirement: YOLO11 目标检测

系统 SHALL 使用 YOLO11n（COCO 预训练，`yolo11n.pt`）对每帧进行目标检测。SHALL 筛选 `ai-model-capability` spec 定义的 12 类映射 EntityType。检测结果 SHALL 产出 `[{bbox, class_id, confidence, entity_type_id}, ...]`。

#### Scenario: 检测行人

- **WHEN** 视频帧中出现行人
- **THEN** YOLO 检出 person 框，映射 `entity_type_id=1 (PERSON)`，写入 EventBus

#### Scenario: 无目标

- **WHEN** 视频帧中无任何 15 类实体
- **THEN** YOLO 返回空列表，EventBus 无 EntityType 事件

### Requirement: YOLO 状态机

YOLO 模块 SHALL 维护 IDLE → ACTIVE → ERROR 状态机。首帧解码成功 → ACTIVE。推理异常 → 跳过当前帧，状态保持 ACTIVE。连续 10 帧推理失败 → ERROR，记录日志并尝试重新加载模型。

#### Scenario: 推理异常恢复

- **WHEN** 单帧 YOLO 推理抛出异常
- **THEN** 跳过该帧，下一帧继续推理，状态保持 ACTIVE

### Requirement: 置信度阈值

系统 SHALL 提供可配置的置信度阈值（`YOLO_CONFIDENCE`，默认 0.5）。低于阈值的检测框 SHALL 丢弃。

#### Scenario: 低置信度丢弃

- **WHEN** person 框 confidence=0.3 且 `YOLO_CONFIDENCE=0.5`
- **THEN** 该框被丢弃，不产出事件

### Requirement: YOLO device configuration

The system SHALL provide a `YOLO_DEVICE` setting. It SHALL default to `cpu` so local startup does not require CUDA/cuDNN, and deployments MAY override it with a GPU device id such as `0`.

#### Scenario: Default CPU startup

- **WHEN** `YOLO_DEVICE` is not set in `.env` or the process environment
- **THEN** the YOLO detector loads the model on `cpu`
- **AND** startup does not fail because the setting is missing

#### Scenario: GPU deployment override

- **WHEN** `YOLO_DEVICE=0`
- **THEN** the YOLO detector moves the model to GPU device `0`

# Delta: AI Model Capability — 车辆检测行为更新

## MODIFIED Requirements

### Requirement: YOLO11 目标检测模型

系统 SHALL 使用 YOLO11n（COCO 预训练）作为默认目标检测模型，权重文件存放于 `src/third-party/yolo/yolo11n.pt`（5.4 MB）。

YOLO11 COCO 80 类中 SHALL 映射到 `EntityType` 枚举的类别为：

| EntityType 枚举 | COCO 类 |
|-----------------|---------|
| PERSON (1) | person (0) |
| CAR (2) | car (2) |
| TRUCK (3) | truck (7) |
| BUS (4) | bus (5) |
| MOTORCYCLE (5) | motorcycle (3) |
| BICYCLE (6) | bicycle (1) |
| DOG (7) | dog (16) |
| CAT (8) | cat (15) |
| BIRD (9) | bird (14) |
| BACKPACK (10) | backpack (24) |
| SUITCASE (11) | suitcase (28) |
| KNIFE (12) | knife (43) |

COCO 12/12 类全覆盖。

车辆类实体 SHALL 在主管线中被抑制绘制（不在 Person/Knife 的 `draw_detections` 中渲染），改由 `VehicleProcessor` 旁路独立处理：蓝色框标注、车辆类别名标签、累计统计。

#### Scenario: 检测行人

- **WHEN** 视频帧中出现行人
- **THEN** 系统输出 `EntityType.PERSON`，可用于电子围栏、人数统计

#### Scenario: 检测已知物件

- **WHEN** 画面中出现刀具（knife）
- **THEN** 系统输出 `EntityType.KNIFE`，触发异常物品告警

#### Scenario: 检测车辆 — 旁路处理

- **WHEN** 视频帧中出现轿车（car）
- **THEN** YOLO 输出 `EntityType.CAR` 的 Detection
- **AND** 主绘管线抑制该检测（不通过 `draw_detections` 渲染）
- **AND** `VehicleProcessor` 旁路用蓝色框标注 "轿车"、执行去重、更新统计

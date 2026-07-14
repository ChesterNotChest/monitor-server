# Vehicle Detection Bypass

车辆检测旁路处理器——独立的 Frame Hook，从 YOLO 检测结果中过滤车辆类 Detection，蓝色框标注，简单 IoU 去重，累计统计。

## ADDED Requirements

### Requirement: VehicleProcessor 注册为独立 Frame Hook

系统 SHALL 在 `AIPipeline` 中注册 `VehicleProcessor.process_frame` 为独立的 Frame Hook，执行顺序在 `VideoAIProcessor.process_frame` 之后。车辆 hook SHALL 不修改、不依赖 `VideoAIProcessor` 的任何内部状态。

#### Scenario: Hook 注册顺序

- **WHEN** `register_video_ai_hooks()` 被调用
- **THEN** `VideoAIProcessor.process_frame` 被注册为第一个 hook
- **AND** `VehicleProcessor.process_frame` 被注册为第二个 hook
- **AND** 两个 hook 在管线主循环中按注册顺序依次执行

#### Scenario: 车辆 hook 独立于人物 hook 运行

- **WHEN** `VideoAIProcessor.process_frame` 执行失败或跳过
- **THEN** `VehicleProcessor.process_frame` 仍然正常执行
- **AND** 车辆检测不受人物管线故障影响

### Requirement: 车辆类 Detection 过滤

系统 SHALL 从 YOLO 的 `detections` 列表中过滤出 `entity_type_id` 属于 5 种车辆类型的 Detection：CAR (2)、TRUCK (3)、BUS (4)、MOTORCYCLE (5)、BICYCLE (6)。

#### Scenario: 过滤车辆 Detection

- **WHEN** YOLO 返回 10 个 Detection（包含 3 个 person、2 个 car、1 个 truck、1 个 bus、1 个 dog、1 个 knife、1 个 motorcycle）
- **THEN** VehicleProcessor 仅处理 5 个 Detection（2 car + 1 truck + 1 bus + 1 motorcycle）
- **AND** person、dog、knife Detection 被忽略

#### Scenario: 无车辆

- **WHEN** 当前帧中 YOLO 未检测到任何车辆类 Detection
- **THEN** VehicleProcessor 不绘制任何车辆框
- **AND** `current_frame` 统计中各类型计数均为 0

### Requirement: 蓝色框车辆标注

系统 SHALL 用蓝色 `(255, 0, 0)` 绘制车辆检测框和类别标签。框厚度 SHALL 为 2px，标签字体 SHALL 为 `FONT_HERSHEY_SIMPLEX` 0.5 比例。标签内容格式为 `{中文类别名}`（如 "轿车"、"卡车"、"公交车"、"摩托车"、"自行车"）。

#### Scenario: 单帧多车标注

- **WHEN** 画面中同时检测到 car 和 truck
- **THEN** 画面上出现蓝色框标注 "轿车" 和 "卡车"
- **AND** 车辆框独立于人物框（绿/黄/红）绘制，互不覆盖

#### Scenario: 车辆与人物重叠

- **WHEN** 画面中一辆 car 与一个 person 的 bbox 高度重叠
- **THEN** car 的蓝色框和 person 的绿色框各自独立绘制
- **AND** 两个框可能部分重叠，但颜色不同可区分

### Requirement: 简单 IoU 跨帧去重

系统 SHALL 使用网格哈希 + IoU 方法对相邻帧中同类车辆进行去重。帧画面 SHALL 被划分为 16×16 网格。每辆车落入的网格单元 SHALL 记录其 class 和 bbox。连续帧中，同一网格单元内同 class 且 IoU > 0.5 的检测 SHALL 视为同一车辆，不重复计数。去重记录 SHALL 每 30 帧（约 2 秒 @ 15fps）清理一次。

#### Scenario: 同一车辆连续帧不去重

- **WHEN** 同一辆 car 在连续 10 帧中出现，位置基本不变
- **THEN** `total_unique` 中 car 的计数仅增加 1
- **AND** 后续帧不再为该车增加计数

#### Scenario: 不同位置的新车辆

- **WHEN** 第一帧在画面左侧检测到 car，第二帧在画面右侧检测到另一辆 car，两车网格不重叠
- **THEN** `total_unique` 中 car 的计数增加 2

#### Scenario: 去重窗口过期

- **WHEN** 一辆 car 在第 1 帧出现后离开，第 35 帧重新出现
- **THEN** 如果 30 帧清理周期已过，该车可能被计为新车辆
- **AND** 此行为是可接受的——车辆大概率是不同车辆

### Requirement: 累计车辆统计

系统 SHALL 在 `VehicleProcessor` 实例中维护累计统计 `total_unique: dict[str, int]` 和当前帧统计 `current_frame: dict[str, int]`。累计统计 SHALL 在管线启动时初始化为 0，随帧处理递增，管线停止时丢弃。车辆类别键 SHALL 使用英文名：`car`、`truck`、`bus`、`motorcycle`、`bicycle`。

#### Scenario: 管线启动时统计归零

- **WHEN** 一个 View 的 AI 管线被创建并启动
- **THEN** `VehicleProcessor` 的 `total_unique` 中所有车辆类别计数均为 0

#### Scenario: 累计统计递增

- **WHEN** 检测到 3 辆新车（1 car + 2 bus）
- **THEN** `total_unique["car"]` 增加 1
- **AND** `total_unique["bus"]` 增加 2
- **AND** 其他类别不变

#### Scenario: 管线停止时统计丢弃

- **WHEN** View 被删除或管线停止
- **THEN** 该 View 的车辆统计数据被丢弃
- **AND** 不写入数据库

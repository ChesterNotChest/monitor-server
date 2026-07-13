# Fence TOO_CLOSE Detection

**Purpose:** 安全距离缓冲区——YOLO 检测框靠近围栏但未进入时触发 TOO_CLOSE 告警。

## Requirements

### Requirement: 安全距离配置
系统 SHALL 允许为电子围栏配置 `safe_distance` 像素值（默认 0 = 禁用 TOO_CLOSE），该值表示围栏多边形各边向外平移的像素距离。

#### Scenario: 启用安全距离
- **WHEN** 创建围栏时设置 `safe_distance=50`
- **THEN** 围栏检测引擎计算扩展多边形（原始多边形各边向外平移 50 像素），YOLO 检测框在扩展区内但不在原始区内时触发 TOO_CLOSE

#### Scenario: 禁用安全距离
- **WHEN** 创建围栏时设置 `safe_distance=0` 或不传该字段
- **THEN** 不计算扩展多边形，不触发 TOO_CLOSE 事件，行为与原有 ENTERED/EXITED 一致

### Requirement: TOO_CLOSE 事件生产
系统 SHALL 在每帧检测时，对每个 track 评估原始围栏多边形与扩展多边形的关系，产生 TOO_CLOSE 事件。

#### Scenario: Track 进入安全距离区
- **WHEN** YOLO 检测框与扩展多边形有交集且与原始围栏多边形无交集
- **THEN** 系统发布 `FenceEvent(result=TOO_CLOSE, entered=True)` 到 EventBus FENCE topic，状态机从 NOT_ENTERED 切换到 TOO_CLOSE

#### Scenario: Track 离开安全距离区
- **WHEN** Track 处于 TOO_CLOSE 状态且 YOLO 检测框离开扩展多边形
- **THEN** 系统发布 `FenceEvent(result=TOO_CLOSE, entered=False)`，状态机从 TOO_CLOSE 回到 NOT_ENTERED

#### Scenario: 从 TOO_CLOSE 进入围栏
- **WHEN** Track 处于 TOO_CLOSE 状态且 YOLO 检测框进入原始围栏多边形
- **THEN** 系统开始 `entry_delay_seconds` 计时器，超时后发布 ENTERED 事件（参见 fence-entry-delay 规范）

### Requirement: TOO_CLOSE 事件消费
系统 SHALL 在标注层和告警匹配层正确识别 TOO_CLOSE 事件。

#### Scenario: 标注层更新 TOO_CLOSE 标签
- **WHEN** `_on_fence_event` 收到 `result="TOO_CLOSE"` 且 `entered=True`
- **THEN** `_fence_labels[tid]` 设为 `"Fence-{id}:TOO_CLOSE"`，绘制层可据此标注

#### Scenario: 告警引擎识别 TOO_CLOSE
- **WHEN** `get_active_signals()` 从 `_fence_labels` 提取活跃的围栏事件
- **THEN** 标签含 `:TOO_CLOSE` 时 `fence_result_ids` 集合包含 `FenceEventResult.TOO_CLOSE (2)`

#### Scenario: TOO_CLOSE 告警规则匹配
- **WHEN** ExceptionDef 配置 `fence_event_id=2`
- **THEN** 当 `ActiveSignals.fence_result_ids` 包含 `{2}` 且 ExceptionDef 其他条件也满足时，系统触发告警

### Requirement: TOO_CLOSE 扩展多边形绘制
系统 SHALL 在标注帧上以红色细线绘制扩展多边形，区别于原始围栏的橙色填充。

#### Scenario: 扩展多边形可视化
- **WHEN** 该 View 下至少一个围栏的 `safe_distance > 0`
- **THEN** 在标注帧上绘制对应扩展多边形（红色细线，1px，LINE_AA），与原始围栏橙色填充叠加显示

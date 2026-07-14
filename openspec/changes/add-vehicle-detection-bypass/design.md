## Context

当前 `AIPipeline._run_loop()` 中 YOLO11 已能检测 5 种车辆（car, truck, bus, motorcycle, bicycle），但 `_enrich_detection_labels()` 将其列为 `_SUPPRESSED_ENTITIES`，`label_suffix` 永远为 `None`，`draw_detections()` 跳过不绘制。车辆信息在当前管线中被白白丢弃。

系统已内建 Frame Hook 机制（`AIPipeline._frame_hooks: list[FrameHook]`），当前仅注册了 `VideoAIProcessor.process_frame` 一个 hook。这个扩展点是天然的旁路插入位置。

约束：
- 强解耦：不修改 `VideoAIProcessor`、`ByteTracker`、`FaceRecognizer`、`SlowFastRunner`、`FenceEngine` 等现有 Part B 模块
- 同通路：车辆框直接画在现有 `/view/{id}` 标注流上，不推独立流
- 无数据库变更：统计数据为内存态，随管线生命周期

## Goals / Non-Goals

**Goals:**
- 在 YOLO 检测结果中过滤出 5 类车辆，用蓝色框独立标注
- 简单 IoU 跨帧去重（相邻帧同位置同类 = 同一辆），不做跨遮挡跟踪
- 累计统计从管线启动至今出现的各类车辆数（去重后的唯一车辆数）
- 提供 REST API 查询 View 的车辆统计数据
- 前端独立页面 `/vehicle-monitor`：View 选择器 + 直播预览 + 饼图 + 分类统计表

**Non-Goals:**
- 不做复杂的车辆跟踪（无 ByteTrack for vehicles）
- 不推独立视频流
- 不触发告警、不写数据库、不录制回放
- 不侵入现有的 Person 检测管线
- 不需要 YOLO 重新训练或换模型

## Decisions

### Decision 1: VehicleProcessor 作为独立 Frame Hook

**选择**: 新增 `VehicleProcessor` 类，通过 `pipeline.register_frame_hook()` 注册为第二个 hook，在 `VideoAIProcessor.process_frame` 之后执行。

**替代方案**: 在 `_enrich_detection_labels()` 中分支处理车辆 → 拒绝。原因：
- 会污染现有的 label enrichment 逻辑（目前清晰分为 Person / Knife / Suppressed）
- `label_suffix` 的语义是"告警标签"，车辆统计不需要告警标签
- 车辆处理器有自己的去重和统计状态，不应耦合到 label enrichment 中

**执行顺序**: `VideoAIProcessor.process_frame` → `VehicleProcessor.process_frame`。车辆 hook 在后面执行，可以确保人物追踪/人脸/行为等重量级模块不受影响。

### Decision 2: 蓝色框绘制独立于 `draw_detections()`

**选择**: 新增 `draw_vehicle_detections(frame, vehicle_detections)` 函数，用蓝色 `(255, 0, 0)` 绘制车辆框。

**替代方案**: 修改 `draw_detections()` 增加车辆参数 → 拒绝。原因：
- `draw_detections()` 按 `alert_level` 着色（绿/黄/红），车辆不需要 alert_level
- 车辆框的颜色语义独立（蓝色 = 旁路统计），不应混入告警色体系

### Decision 3: 简单 IoU 去重，不引入 ByteTracker

**选择**: 在 `VehicleProcessor` 内部维护 `_seen_vehicles: dict[str, set[int]]` — 按 vehicle_class 分组，存储最近 N 帧内见过该类的 bbox 标识（基于网格哈希 + IoU > 0.5 判定为同一辆）。

**算法**:
1. 将帧划分为 16×16 网格
2. 每辆车落入 1-4 个网格单元
3. 检查该网格单元中是否有相同 class 的历史记录
4. 如果网格命中 + IoU > 0.5 → 同一辆车，不增加计数
5. 如果全新 → 计数 +1，记录网格位置
6. 每 30 帧清理一次过期记录（约 2 秒 @ 15fps）

**替代方案**: 用 ByteTracker 跟踪车辆 → 拒绝。原因：
- ByteTracker 目前硬编码为 Person-only filter
- 车辆跟踪需要单独的 tracker 实例和调参
- 简单 IoU 去重对"计数唯一车辆"的场景足够（不需要跨遮挡重识别）

### Decision 4: 统计数据结构为内存态

**选择**: `VehicleStats` 存储在 `VehicleProcessor` 实例中，包含：
```python
@dataclass
class VehicleStats:
    total_unique: dict[str, int]     # {"car": 15, "truck": 3, ...}
    current_frame: dict[str, int]    # 当前帧去重后的车辆数
    fps: float                       # 当前统计帧率
```

View 创建时初始化，管线停止时丢弃。API 通过独立的 `_vehicle_processors` 注册表读取（见 Decision 7）。

**替代方案**: 写 SQLite 表持久化 → 拒绝。原因：
- 车辆统计是实时观测数据，无长期存储需求
- 减少数据库 schema 变更和写入开销
- 与 "强解耦" 原则一致

### Decision 5: 前端独立页面 /vehicle-monitor

**选择**: 新增独立路由 `/vehicle-monitor`，页面结构：
```
┌────────────────────────────────────────────┐
│  车辆监控              [View 下拉选择器]    │
├──────────────────────┬─────────────────────┤
│                      │  车辆类型分布         │
│   直播预览           │  ┌─────────────┐     │
│   (WHEP/FLV)        │  │  饼图 SVG   │     │
│                      │  └─────────────┘     │
│                      │                     │
│                      │  分类统计            │
│                      │  Car:     15 辆     │
│                      │  Truck:    3 辆     │
│                      │  Bus:      2 辆     │
│                      │  Motor:    8 辆     │
│                      │  Bicycle:  5 辆     │
│                      │                     │
│                      │  总计:    33 辆     │
├──────────────────────┴─────────────────────┤
│  当前帧: Car:2  Truck:0  Bus:1  Motor:1   │
└────────────────────────────────────────────┘
```

- 左侧：复用 `useWhepPlayer` / `useFlvPlayer` 进行直播预览
- 右上：纯 SVG 饼图（与现有 TrendChart 风格一致，无外部依赖）
- 右下：分类统计表 + 总计
- 底部：当前帧实时计数条

### Decision 6: API 设计

**选择**: `GET /api/v1/views/{view_id}/vehicle-stats/`

响应体：
```json
{
  "view_id": 1,
  "total_unique": {"car": 15, "truck": 3, "bus": 2, "motorcycle": 8, "bicycle": 5},
  "current_frame": {"car": 2, "truck": 0, "bus": 1, "motorcycle": 1, "bicycle": 0},
  "fps": 15.2
}
```

不新增 RBAC 权限，沿用 `dashboard:view`（与仪表盘同级）。

### Decision 7: VehicleProcessor 实例通过独立注册表暴露给 API 层

**选择**: 在 `vision_task.py` 中维护独立的 `_vehicle_processors: dict[int, VehicleProcessor]` 注册表，与 `_active_pipelines` 同级。

```python
# vision_task.py
_active_pipelines: dict[int, AIPipeline] = {}
_vehicle_processors: dict[int, VehicleProcessor] = {}  # NEW
_alert_engines: dict[int, AlertEngine] = {}
```

**生命周期**:
- `start_pipeline()` → 创建 `VehicleProcessor` 实例 → 注册 hook + 存入 `_vehicle_processors[view_id]`
- `stop_pipeline()` → 从 `_vehicle_processors.pop(view_id)` 清理

**API 访问路径**:
```
GET /api/v1/views/{view_id}/vehicle-stats/
  → vehicle_router.py
  → from src.service.vision_task import _vehicle_processors
  → processor = _vehicle_processors.get(view_id)
  → processor.get_stats()
```

**替代方案**: 将 `VehicleProcessor` 挂载到 `AIPipeline` 实例属性上（如 `pipeline.vehicle_processor`）→ 拒绝。原因：
- `AIPipeline` 是通用调度器，不应持有特定旁路模块的引用
- 独立注册表与 `_alert_engines`、`_yamnet_runners` 模式一致，符合现有代码风格
- 强解耦：`AIPipeline` 完全不需要知道 `VehicleProcessor` 的存在
- 如果未来有更多旁路模块（如动物统计、物品统计），都走独立注册表即可

## Risks / Trade-offs

- **[R] 车辆在画面中短暂出现即消失 → 被计为多辆**: 当前 30 帧去重窗口（约 2 秒）内，如果同一辆车离开视野再进入，会被计为新车辆。这是可接受的偏差——我们目标是"大概数量级"而非精确计数。
- **[R] YOLO confidence=0.5 阈值对远处小车可能漏检**: 可通过配置项 `VEHICLE_CONFIDENCE` 独立调整，默认 0.4（比 Person 的 0.5 更低，因为车辆 box 通常更大更易检测）。
- **[R] 同帧多辆同类型车 → IoU 去重可能误合并**: 如果两辆同色同型号车在画面中高度重叠，可能被合并为一辆。Edge case，概率低，可接受。
- **[R] 内存统计数据在 Server 重启后丢失**: 设计如此。统计是实时观测快照，不承诺持久化。如未来需要，可接入 `ReportSetting` 做定时快照。
- **[R] 前端无专用图表库，纯 SVG 饼图需手写**: 饼图比柱状图复杂（需要 arc path 计算），但可内联实现，约 80 行 SVG 生成函数。

## Open Questions

- 无。所有关键设计决策已在探索阶段对齐。

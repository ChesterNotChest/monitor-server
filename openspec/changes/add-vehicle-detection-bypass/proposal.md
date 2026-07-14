## Why

YOLO11 已经能检测 5 种车辆（car, truck, bus, motorcycle, bicycle），但当前管线中车辆检测结果被标记为 `_SUPPRESSED_ENTITIES`，检测信息白白丢弃。在监控场景中，车辆流量统计是一个独立且高价值的旁路能力——与人员安防逻辑完全解耦，不需要人脸、行为、围栏等重量级模块。

## What Changes

- **新增 VehicleProcessor**：作为独立的 Frame Hook 注册到 `AIPipeline`，过滤车辆类 Detection，执行简单 IoU 跨帧去重，用蓝色框绘制车辆标注（独立于现有人物标注）
- **累计车辆统计**：内存中维护每 View 的车辆类型计数器（car/truck/bus/motorcycle/bicycle），从管线启动累计至今
- **新增车辆统计 API**：`GET /api/v1/views/{view_id}/vehicle-stats/` 返回当前 View 的车辆类型分布和实时帧计数
- **新增前端页面**：`/vehicle-monitor` 独立页面，包含 View 选择器、直播预览、车辆类型饼图、分类统计表
- **管线修改**：在 `_run_loop()` 中插入车辆绘制调用（`draw_vehicle_detections`），与现有人物绘制在同一帧上叠加

## Capabilities

### New Capabilities
- `vehicle-detection-bypass`: 车辆检测旁路处理器——独立的 Frame Hook，过滤 YOLO 车辆检测结果，蓝色框标注，IoU 去重，累计统计
- `vehicle-stats-api`: 车辆统计 REST API——`GET /api/v1/views/{view_id}/vehicle-stats/` 返回累计和实时车辆计数
- `vehicle-monitor-page`: 前端车辆监控页面——View 选择器 + 直播预览 + 饼图 + 分类统计表

### Modified Capabilities
- `ai-model-capability`: 车辆类别从「可检测但抑制」变为「旁路独立处理」，更新车辆检测的行为描述
- `view-management`: View 获取时不新增字段，但车辆旁路的生命周期绑定到 View 的 AI 管线启动/停止

## Impact

- **Vision 模块**: 新增 `vision_vehicle/` 包（`processor.py`），修改 `vision_pipeline.py`（绘制调用）、`vision_annotation.py`（蓝色框绘制函数）、`vision_task.py`（注册 hook）
- **API 层**: 新增 `vehicle_router.py`，注册到 `__init__.py`
- **前端**: 新增 `VehicleMonitor.tsx` 页面、`/vehicle-monitor` 路由、`fetchVehicleStats()` API 调用
- **配置**: 新增车辆检测相关可选配置项（置信度阈值、IoU 阈值、去重 TTL）
- **不修改**: `VideoAIProcessor`、`ByteTracker`、`FaceRecognizer`、`SlowFastRunner`、`FenceEngine` 等现有 Part B 模块
- **不新增数据库表**: 统计数据为内存态，随管线生命周期

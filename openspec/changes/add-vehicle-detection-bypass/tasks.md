## 1. Vision — VehicleProcessor 核心

- [x] 1.1 新建 `src/service/vision_module/vision_vehicle/` 包（`__init__.py` + `processor.py`）
- [x] 1.2 实现 `VehicleProcessor` 类：接收配置参数，维护 `total_unique` / `current_frame` 计数器，维护网格哈希去重状态
- [x] 1.3 实现 `process_frame(ctx: FrameContext)` 方法：从 `ctx.detections` 中过滤车辆类 Detection，执行 IoU 去重，填充 `ctx.vehicle_detections`
- [x] 1.4 实现车辆类别中文名映射（car→轿车, truck→卡车, bus→公交车, motorcycle→摩托车, bicycle→自行车）
- [x] 1.5 实现 `get_stats()` 方法返回 `VehicleStats` 数据结构

## 2. Vision — 绘制集成

- [x] 2.1 在 `vision_annotation.py` 中新增 `draw_vehicle_detections(frame, vehicle_detections)` 函数：蓝色框 `(255, 0, 0)` + 中文标签
- [x] 2.2 在 `vision_pipeline.py` 的 `FrameContext` dataclass 中新增 `vehicle_detections: list[Detection] = field(default_factory=list)` 字段
- [x] 2.3 在 `vision_pipeline.py` 的 `_run_loop()` 中，hook 执行后调用 `draw_vehicle_detections()`（在 `draw_detections()` 之后、`push_frame()` 之前）
- [x] 2.4 确保车辆绘制不影响现有 Person/Knife 检测的绘制和 push 管线

## 3. Pipeline 集成

- [x] 3.1 在 `vision_task.py` 中创建 `VehicleProcessor` 实例、存入独立注册表 `_vehicle_processors: dict[int, VehicleProcessor]`、注册 `process_frame` 为第二个 hook
- [x] 3.2 `_vehicle_processors` 与 `_active_pipelines` 同级维护，`start_pipeline` 时注册、`stop_pipeline` 时清理
- [x] 3.3 确保 View 管线停止时 VehicleProcessor 状态被清理

## 4. API 层

- [x] 4.1 新建 `src/schema/http/vehicle_schema.py`：`VehicleStatsResponse` Pydantic 模型
- [x] 4.2 新建 `src/network/api/vehicle_router.py`：`GET /api/v1/views/{view_id}/vehicle-stats/` 端点
- [x] 4.3 在 `src/network/api/__init__.py` 的 `routers` 列表中注册 `vehicle_router`
- [x] 4.4 端点从 `src.service.vision_task._vehicle_processors` 获取对应 View 的 `VehicleProcessor` 实例，调用 `get_stats()` 返回数据

## 5. 配置

- [x] 5.1 在 `src/config.py` 中新增可选配置项：`VEHICLE_CONFIDENCE`（默认 0.4）、`VEHICLE_IOU_THRESHOLD`（默认 0.5）、`VEHICLE_DEDUP_FRAMES`（默认 30）
- [x] 5.2 在 `.env` 文件中添加默认值（可选，硬编码默认值已可用）

## 6. 前端 — 页面与路由

- [x] 6.1 新建 `src/pages/VehicleMonitor.tsx` 页面组件骨架（View 选择器 + 左右分栏布局）
- [x] 6.2 实现 View 选择器：调用 `fetchViews()` 获取列表，下拉切换选中 View
- [x] 6.3 实现直播预览区：复用 `useWhepPlayer` / `useFlvPlayer` hooks
- [x] 6.4 在 `src/router/index.tsx` 中添加 `/vehicle-monitor` 路由（AuthGuard + AppLayout 内，与 MainDashboard 同级）
- [x] 6.5 在 `src/components/layout/Sidebar.tsx` 中添加「车辆监控」导航菜单项

## 7. 前端 — 统计图表

- [x] 7.1 在 `src/api/client.ts` 中添加 `fetchVehicleStats(viewId)` API 调用函数
- [x] 7.2 在 `src/api/types.ts` 中添加 `VehicleStatsResponse` TypeScript 类型
- [x] 7.3 实现 SVG 饼图组件（纯内联 SVG，无外部依赖）：5 种车辆颜色映射、扇区 arc 计算、图例
- [x] 7.4 实现分类统计表：中文名 + 色块 + 累计计数 + 底部总计行
- [x] 7.5 实现底部当前帧计数条
- [x] 7.6 实现 2 秒轮询 `fetchVehicleStats()` 自动刷新（离开页面时清除定时器）
- [x] 7.7 处理空状态（无 View 选中、无车辆数据、API 错误）

## 8. 验证

- [x] 8.1 启动 SRS + Server + Node（按 playbook），创建 View 后验证 API 返回统计数据
- [x] 8.2 验证视频流中出现蓝色车辆框 + 中文标签
- [x] 8.3 验证前端页面 `/vehicle-monitor`：View 选择 → 预览加载 → 饼图/统计表 → 实时帧计数
- [x] 8.4 验证车辆去重：同一辆车连续出现不重复计数
- [x] 8.5 验证现有 Person 检测、绘制、告警不受影响（回归测试）

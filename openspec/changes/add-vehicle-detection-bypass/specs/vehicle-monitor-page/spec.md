# Vehicle Monitor Page

前端车辆监控页面 — View 选择器 + 直播预览 + 车辆类型饼图 + 分类统计表。

## ADDED Requirements

### Requirement: 独立路由页面

系统 SHALL 在 `/vehicle-monitor` 提供独立的车辆监控页面。页面 SHALL 受 AuthGuard 保护，仅登录用户可访问。页面 SHALL 在侧边栏导航菜单中有入口（与 MainDashboard 同级）。

#### Scenario: 导航到车辆监控页面

- **WHEN** 已登录用户点击侧边栏「车辆监控」菜单项
- **THEN** 浏览器导航到 `/vehicle-monitor`
- **AND** 页面显示 View 选择器、直播预览、饼图、统计表

#### Scenario: 未登录访问

- **WHEN** 未登录用户直接访问 `/vehicle-monitor`
- **THEN** 重定向到 `/login`

### Requirement: View 选择器

页面顶部 SHALL 提供 View 下拉选择器，列出所有已创建的 View（通过 `GET /api/v1/views/` 获取）。选择 View 后 SHALL 自动加载该 View 的直播流和车辆统计数据。

#### Scenario: 切换 View

- **WHEN** 用户在 View 下拉选择器中切换到 View 2
- **THEN** 直播预览切换到 View 2 的流
- **AND** 车辆统计切换到 View 2 的数据
- **AND** 饼图和统计表刷新

#### Scenario: 无可用 View

- **WHEN** 系统中没有创建任何 View
- **THEN** 下拉选择器显示 "暂无可用 View"
- **AND** 预览区域显示占位提示

### Requirement: 直播预览

页面左侧（或上方在小屏设备上）SHALL 显示当前选中 View 的直播预览。预览 SHALL 使用与 `LiveMonitor` 相同的双回退策略：WebRTC (WHEP) 优先，FLV (flv.js) 后备。

#### Scenario: WHEP 播放正常

- **WHEN** 选中 View 后 WebRTC 连接成功
- **THEN** 预览区显示低延迟视频流，画面中包含蓝色车辆标注框

#### Scenario: WHEP 失败回退 FLV

- **WHEN** WebRTC 连接超时或失败
- **THEN** 自动切换到 flv.js 播放器
- **AND** 视频流正常播放

#### Scenario: 两种播放方式均失败

- **WHEN** WHEP 和 FLV 均无法播放
- **THEN** 预览区显示错误信息 "无法连接视频流"

### Requirement: 车辆类型饼图

页面右侧 SHALL 显示车辆类型分布的 SVG 饼图。饼图 SHALL 基于 `total_unique` 数据绘制，5 种车辆类型各用不同颜色区分。饼图 SHALL 无外部图表库依赖。

#### Scenario: 饼图显示数据

- **WHEN** 选中 View 的 `total_unique` 为 `{"car": 15, "truck": 3, "bus": 2, "motorcycle": 8, "bicycle": 5}`
- **THEN** 饼图显示 5 个扇区，大小比例对应 15:3:2:8:5
- **AND** 每个扇区有不同颜色和中文标签

#### Scenario: 无车辆数据

- **WHEN** 所有 `total_unique` 值均为 0
- **THEN** 饼图显示空状态占位符 "暂无车辆数据"
- **AND** 不显示空白饼图

### Requirement: 分类统计表

饼图下方 SHALL 显示分类统计表，包含每类车辆的中文名、图标/颜色标识、累计计数。底部 SHALL 显示总计数字。

#### Scenario: 统计表展示

- **WHEN** 车辆统计数据更新
- **THEN** 统计表显示 5 行：轿车、卡车、公交车、摩托车、自行车
- **AND** 每行显示对应类别的累计计数
- **AND** 底部显示所有类别的总计

### Requirement: 实时帧计数

页面底部 SHALL 显示当前帧的实时车辆计数条（基于 `current_frame`），每 2 秒自动轮询更新一次。

#### Scenario: 实时帧计数自动刷新

- **WHEN** 页面处于活跃状态
- **THEN** 每 2 秒发送一次 `GET /api/v1/views/{view_id}/vehicle-stats/` 请求
- **AND** `current_frame` 数据实时更新显示
- **AND** `total_unique` 数据同步更新（饼图和统计表）

#### Scenario: 页面离开时停止轮询

- **WHEN** 用户导航离开 `/vehicle-monitor` 页面
- **THEN** 轮询定时器被清除
- **AND** 不再发送 API 请求

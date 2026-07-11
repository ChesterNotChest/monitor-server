## ADDED Requirements

### Requirement: View 查询响应必须包含播放 URL

系统 SHALL 在 `GET /api/v1/views/{view_id}` 和 `GET /api/v1/views` 的响应中为每个 View 填充非空的 `flv_url`、`webrtc_url` 和 `rtmp_url` 字段。URL 的生成 SHALL 委托给 `build_play_urls(view_id)`，与 `POST /api/v1/views` 创建流程使用相同的地址构建逻辑。

当 `DEBUG_WEB_STREAM=true` 时，`flv_url` 和 `webrtc_url` SHALL 为 `None`（调试模式仅提供 RTMP 直连）。当 `DEBUG_WEB_STREAM=false`（SRS 生产模式）时，三个 URL 字段 SHALL 全部非空。

#### Scenario: 获取单个 View 时返回播放 URL

- **WHEN** 前端请求 `GET /api/v1/views/{view_id}` 且 `DEBUG_WEB_STREAM=false`
- **THEN** 响应的 `flv_url` SHALL 格式为 `http://{host}:{port}/view/{view_id}.flv`
- **AND** `webrtc_url` SHALL 格式为 `http://{host}:{port}/rtc/v1/whep/?app=view&stream={view_id}`
- **AND** `rtmp_url` SHALL 格式为 `rtmp://{host}:{port}/view/{view_id}`

#### Scenario: 列表查询时每个 View 都带播放 URL

- **WHEN** 前端请求 `GET /api/v1/views` 且 `DEBUG_WEB_STREAM=false`
- **THEN** 返回的每个 View 对象 SHALL 包含非空的 `flv_url`、`webrtc_url`、`rtmp_url`

#### Scenario: 调试模式下 FLV/WebRTC URL 为空

- **WHEN** `DEBUG_WEB_STREAM=true`
- **THEN** `flv_url` 和 `webrtc_url` SHALL 为 `None`，`rtmp_url` SHALL 指向 `rtmp://127.0.0.1:1936/view/{view_id}`

### Requirement: SRS HTTP 服务器允许跨域访问

SRS 的 `http_server` 配置 SHALL 启用 `crossdomain on;`，允许前端开发服务器（`localhost:5173`）通过 HTTP-FLV 和 WHEP 端点拉取流媒体资源。

#### Scenario: 前端跨域拉流不被拦截

- **WHEN** 前端 `localhost:5173` 向 SRS `localhost:8080` 发起 HTTP-FLV 或 WHEP 请求
- **THEN** 浏览器不因 CORS 策略拦截请求

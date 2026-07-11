## Why

`GET /api/v1/views/{id}` 和 `GET /api/v1/views` 返回的 `ViewResponse` 中 `flv_url`、`webrtc_url`、`rtmp_url` 全部为 `None`，导致前端 LiveMonitor 无法播放视频（显示相机占位符）。根因是 `get_view()` 和 `list_views()` 只返回 ORM 对象，没有调用 `build_play_urls()` 填充流媒体 URL。同时，SRS HTTP 服务器缺少 CORS 配置，前端 `localhost:5173` → SRS `:8080` 会被浏览器拦截。这些问题阻断了前后端端到端联调。

## What Changes

- **修复 `get_view()` 不返回流媒体 URL**：在 `view_task.py` 的 `get_view()` 中调用 `build_play_urls()` 并合并到响应
- **修复 `list_views()` 不返回流媒体 URL**：在 `view_task.py` 的 `list_views()` 中为每个 View 填充 URL
- **SRS 配置添加 CORS**：在 `srs/srs.conf` 的 HTTP 服务器段添加 `crossdomain on;`
- **验证回放流端点**：确认 `GET /recordings/{id}/stream` 返回可播放的 FLV 二进制流
- **验证 `build_play_urls()` 在 SRS 模式下的行为**：确保 `DEBUG_WEB_STREAM=false` 时三个 URL 都正确构建

## Capabilities

### New Capabilities
<!-- No new capabilities — this change fixes bugs in existing capabilities, no new feature surface. -->

### Modified Capabilities
<!-- The spec requirements are already correct; the implementation doesn't match. -->
- `view-management`: GET /views 和 GET /views/{id} 的 spec 已要求返回 playback URLs，但实现未填充。此变更修复实现以匹配 spec 要求。

## Impact

- **`src/service/view_task.py`**：`get_view()` 和 `list_views()` 需调用 `build_play_urls()` 填充 URL 字段
- **`srs/srs.conf`**：HTTP 服务器段添加 `crossdomain on;`
- **`src/network/rtmp/pusher.py`**：验证 `build_play_urls()` 在 `DEBUG_WEB_STREAM=false` 时行为正确
- **`src/network/api/replay.py`**：验证录制流端点正常工作
- **前端**：无需修改（已经正确消费 `flv_url` 和 `/recordings/{id}/stream`）

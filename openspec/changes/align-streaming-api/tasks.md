## 1. 修复 `get_view()` 填充流媒体 URL

- [x] 修改 `src/service/view_task.py` 的 `get_view()` 函数
  - 获取 ORM 对象后，调用 `build_play_urls(view_id)` 获取 URL
  - 构造并返回 `ViewResponse` 对象（对齐 `create_view()` 的做法）
  - 若 View 不存在，返回 `None`

## 2. 修复 `list_views()` 填充流媒体 URL

- [x] 修改 `src/service/view_task.py` 的 `list_views()` 函数
  - 获取 ORM 列表后，为每个 View 调用 `build_play_urls(view.id)`
  - 返回 `list[ViewResponse]` 而非 ORM 对象列表

## 3. SRS 配置添加 CORS 支持

- [x] 编辑 `srs/srs.conf`，在 `http_server` 块中添加 `crossdomain on;`

## 4. 验证回放流端点

- [x] 确认 `GET /api/v1/recordings/{id}/stream` 端点存在且返回 FLV 流（FileResponse + video/x-flv MIME）
- [x] 端点实现正确，无需修复

## 5. 端到端验证

- [ ] 启动 SRS + Server + Node 三进程（按 `前后端通讯对齐.md` §五 的启动顺序）
- [ ] 验证 `POST /views` 创建 View → 响应含非空 `flv_url`
- [ ] 验证 `GET /views/{id}` → `flv_url` 非空且格式正确
- [ ] 验证 `GET /views` → 列表中每个 View 的 URL 非空
- [ ] 浏览器访问 `flv_url` 验证 FLV 流可播放
- [ ] 验证前端 LiveMonitor 不再显示占位符

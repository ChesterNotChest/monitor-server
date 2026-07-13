## 1. 虚拟 Node SEED

- [ ] 1.1 在 `seed_admin()` 或新建 `seed_virtual_node()` 中创建常驻虚拟 Node（name="virtual", is_connected=False）
- [ ] 1.2 确保 SEED idempotent — 重复调用不重复插入

## 2. 数据模型调整

- [ ] 2.1 `VideoDevice` 新增 `stream_url` 字段（nullable String 512）
- [ ] 2.2 `MonitorView.audio_id` 改为 `nullable=True`
- [ ] 2.3 运行 DB migration 或重建表

## 3. 自定义流设备 API

- [ ] 3.1 新增 `POST /api/v1/nodes/{node_id}/devices/` 端点，接受 device_type/name/stream_url
- [ ] 3.2 实现 ffprobe 流在线验证（超时 5s，不可达返回 400）
- [ ] 3.3 创建 VideoDevice 或 AudioDevice 记录并 commit

## 4. FrameReader 适配

- [ ] 4.1 `FrameReader.open()` 优先使用 `VideoDevice.stream_url`，其次 `build_pull_url()`
- [ ] 4.2 验证 cv2.VideoCapture 对 RTMP URL 的兼容性

## 5. View 创建 + YAMNet 跳过

- [ ] 5.1 `view_router.py` 的 `create_view` 允许 `audio_id=None`
- [ ] 5.2 `vision_task.start_pipeline` 中 `audio_id=None` 时跳过 YAMNet
- [ ] 5.3 `view_task.create_view` 处理 optional audio_id

## 6. 前端适配

- [ ] 6.1 View 创建设备选择器支持跨 Node 过滤（区分虚拟 Node 设备）
- [ ] 6.2 音频下拉增加"无"选项
- [ ] 6.3 自定义流管理页面（虚拟 Node 的设备 CRUD）

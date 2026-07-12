## Context

当前录制回放基础设施（`replay_task.py`、`FrameRingBuffer`、`RecordingSession`）代码完整，但没有任何生产代码调用它们。AI 管线（`AIPipeline._run_loop()`）已实现逐帧读取→YOLO检测→标注→推流的完整主循环，但在标注完成后没有将帧写入录制缓冲区。AlertEngine 正确地通过 EventBus 发布 `RECORDING` 事件，但没有订阅者消费。

这是三个独立模块之间的集成问题——每个模块本身都正确，但缺少连接代码。

## Goals / Non-Goals

**Goals:**
- AI 管线每帧将标注帧写入录制环形缓冲区
- View 创建/删除时初始化/清理录制缓冲区
- EventBus RECORDING 事件触发录制会话创建/延续
- `EventResponse` 暴露 `recording_id` 字段供前端匹配录制文件
- `ViewResponse` 暴露 `name` 字段供前端 Dashboard 展示

**Non-Goals:**
- 不修改 `replay_task.py` 的现有函数签名（它们已经正确）
- 不修改 `RecordingSession` 或 `FrameRingBuffer` 的内部逻辑
- 不修改 AlertEngine 的 RECORDING 发布逻辑
- 不改变录制文件的存储路径或格式
- 不做 DB 迁移自动化（`name` 列手写 ALTER TABLE 即可）

## Decisions

### Decision 1: 在 `vision_task.py` 中管理录制生命周期

**选择**：`start_pipeline()` 调用 `start_buffer()` + 注册 RECORDING 订阅者；`stop_pipeline()` 调用 `stop_buffer()` + 注销订阅者。

**理由**：
- `vision_task.py` 已经是管线编排的中心——它创建 AIPipeline、AlertEngine、YamnetRunner
- 录制缓冲区与 View 生命周期绑定（一个 View = 一个 Buffer）
- 避免在 AIPipeline 内部引入 replay_task 依赖（AIPipeline 保持视觉管线纯粹性）

### Decision 2: 在 `AIPipeline._run_loop()` 中直接调用 `push_frame()`

**选择**：在 `_run_loop()` 的推流步骤之后，直接 `import replay_task` 并调用 `push_frame()`。

**替代方案**：
- *注册为 FrameHook*：将 `push_frame` 作为一个 hook 注册。❌ hooks 是异步的，而 `push_frame` 是同步的（写内存缓冲区），注册为 hook 增加不必要的复杂性。
- *在 vision_task.py 中做*：❌ vision_task.py 不在主循环中，无法逐帧调用。

**结论**：在 `_run_loop()` 中直接调用是最简单、性能最好的方式。`push_frame()` 只是写内存缓冲区（O(1)），不会阻塞主循环。

### Decision 3: RECORDING 订阅者使用独立 DB Session

**选择**：订阅者回调中通过 `SessionLocal()` 创建独立的数据库会话。

**理由**：
- EventBus 回调是异步的，可能在不同于管线主循环的 context 中执行
- `alert_triggered()` 需要 db session 来创建 Recording 记录
- 使用独立 session 避免与管线其他 DB 操作耦合

### Decision 4: SRS_PUBLIC_HOST 配置策略

**选择**：在 `.env.example` 中提供带注释的示例，实际值由部署环境设置。

**理由**：
- 开发环境（本机）可以用 `127.0.0.1`
- 联调环境需要设置为实际 IP（如 `10.126.59.25`）
- 不应在代码中硬编码

## Risks / Trade-offs

- **[低风险] `push_frame()` 每帧额外调用**：`push_frame()` 只是写 `collections.deque`（O(1)），不影响主循环帧率。
- **[低风险] RECORDING 订阅者生命周期**：使用全局标志 `_recording_subscribed` 确保只注册一次（多个 View 共享同一个订阅者），最后一个 View 停止时注销。
- **[部署风险] `SRS_PUBLIC_HOST` 配置错误**：如果 IP 不可达，Web 端播放失败。→ 日志中记录构建的 URL，方便排查。

### Decision 5: `EventResponse.recording_id` — 在 Schema 中补充而非修改 DB

**选择**：仅在 `EventResponse` Pydantic schema 中添加 `recording_id: int | None = None` 字段。

**理由**：
- `SituationEvent` DB 模型已有 `recording_id` 列（Mapped[int | None]）
- `EventResponse` 使用 `from_attributes=True`，会自动从 ORM 对象映射
- 只需在 schema 中声明字段即可——无需改 DB

### Decision 6: `ViewResponse.name` — DB 加列 + Schema 加字段

**选择**：在 `MonitorView` ORM 模型添加 `name: Mapped[str | None]` 列，在 `ViewResponse` schema 添加 `name: str | None` 字段。同时更新 `view_task.py` 中构造 `ViewResponse` 的代码。

**替代方案**：
- *用 video/audio device name 拼接*：需要 JOIN 查询，且 create 时需额外 fetch。❌
- *不提供 name，靠前端降级*：前端已有降级 `'视图 ${view.id}'`，但 Dashboard 有内联重命名功能，暗示需要持久化 name。❌

**结论**：DB 加列最干净。默认值可用 `f"视图 {view_id}"` 或 NULL（前端降级）。

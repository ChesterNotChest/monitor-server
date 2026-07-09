# Service Layer

**Purpose:** 定义 `src/service/` 目录的内部结构、门户函数与内部逻辑包的职责边界。

## Requirements

### Requirement: Service 层结构

`service/` SHALL 内含门户函数（`*_task.py`）和内部逻辑包（`/*_module/`）。除特别注明外，一个内部逻辑包 SHALL 对应一个门户函数。

#### Scenario: 新业务模块的目录结构

- **WHEN** 为 View 模块创建 service 层代码
- **THEN** 目录包含 `service/view_task.py`（门户）和 `service/view_module/`（内部逻辑包），`view_module/` 下按功能拆分为 `lifecycle.py`、`ffmpeg_manager.py` 等

### Requirement: task 门户函数职责

`*_task.py` SHALL 作为模块的业务入口，主要被 `network/api/` 或其它 `service/` 模块调用。task SHALL 负责编排业务流程，将具体逻辑委托给 `*_module/`。task SHALL 不直接操作数据库（通过 `repository/`）或网络层（通过 `network/`）。

#### Scenario: API 路由调用 task

- **WHEN** 前端请求 `POST /api/v1/views`
- **THEN** Router 调用 `service/view_task.py` 的 `create_view()`，该函数编排引用计数检查、WSS 命令发送、View 记录创建、FFmpeg 启动，将数据库操作委托给 `repository/`，将网络操作委托给 `network/wss/` 和 `network/rtmp/`

#### Scenario: task 之间互相调用

- **WHEN** `view_task.py` 需要获取 Node 信息
- **THEN** 调用 `node_task.py` 的对应函数，而非直接实例化 `NodeRepo`

### Requirement: module 内部逻辑包职责

`/*_module/` SHALL 封装模块的内部逻辑，不对外暴露为 API 入口。module 内的模块 SHALL 可调取 `repository/` 和 `network/` 层完成具体操作。

#### Scenario: lifecycle 模块操作流生命周期

- **WHEN** `view_module/lifecycle.py` 需要检查设备引用计数
- **THEN** 通过 `MonitorViewRepo` 查询数据库，通过 `network/wss/node_handler.py` 的 `send_command()` 向 Node 发送 `UPDATE_STREAM` 命令

#### Scenario: ffmpeg_manager 管理子进程

- **WHEN** `view_module/ffmpeg_manager.py` 需要启动 FFmpeg
- **THEN** 通过 `network/rtmp/puller.py` 和 `network/rtmp/pusher.py` 构建拉流/推流地址，使用 `asyncio.create_subprocess_exec` 启动子进程，进程生命周期由 module 管理

### Requirement: 数据库会话传递

所有 service 层函数的数据库操作 SHALL 通过 `db: Session` 参数接收会话对象，SHALL 不持有全局数据库连接。会话对象的生命周期 SHALL 由 FastAPI 的 `Depends(get_db)` 依赖注入管理。

#### Scenario: task 函数接收数据库会话

- **WHEN** API Router 调用 `view_task.create_view(db, audio_id, video_id)`
- **THEN** `db` 参数由 FastAPI 依赖注入提供，task 内部将所有 `repository/` 调用委托给同一会话

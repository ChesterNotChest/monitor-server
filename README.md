# Monitor Server

基于 FastAPI 的监控服务后端。

## 目录结构

```
monitor-server/
├── src/
│   ├── app.py              # FastAPI 应用实例
│   ├── run.py              # uvicorn 启动入口
│   ├── config.py           # 配置（.env → pydantic-settings）
│   ├── constants.py        # 全局常量
│   ├── extensions.py       # SQLAlchemy 引擎 / 会话 / Base
│   ├── network/            # 网络层（三层体系）
│   │   ├── api/            #   HTTP API 路由
│   │   ├── wss/            #   WebSocket 端点（Node 连接）
│   │   └── rtmp/           #   RTMP 地址构建
│   ├── models/             # SQLAlchemy 数据模型
│   ├── schema/             # Pydantic 请求 / 响应模型
│   │   ├── http/           #   HTTP API Schema
│   │   └── wss/            #   WebSocket 命令 Schema
│   ├── service/            # 业务逻辑层
│   │   ├── view_module/    #   View 生命周期 + FFmpeg 合流
│   │   └── node_stream_module/  # Node 连接事件处理
│   ├── repository/         # 数据仓库层（BaseRepo + 每模型一个 Repo）
│   └── tests/              # 测试
├── tools/
│   └── rtmp_debug_server.js  # Debug RTMP 靶子（node-media-server）
├── requirements.txt
├── .env
└── Dockerfile
nginx/
│   └── nginx.conf           # Nginx 反向代理配置
docker-compose.prod.yml      # Docker Compose 生产编排
Jenkinsfile                  # Jenkins CI/CD 流水线
```

---

## Miniconda 部署（无需 Docker）

### 1. 创建 & 激活环境（推荐）

仓库内已提供 Server 侧 Conda 环境文件：

```bash
cd monitor-server
conda env create -f environment.yml
conda activate monitor-server
```

该环境会安装：

- `python=3.12`
- `ffmpeg`：Server 侧拉取 audio/video 并合并推流需要
- `nodejs`：`DEBUG_WEB_STREAM=true` 时启动本地 RTMP 靶子需要
- `requirements.txt` 中的 Python 依赖

如果环境已存在，可更新：

```bash
cd monitor-server
conda env update -f environment.yml --prune
conda activate monitor-server
```

### 2. 安装依赖（仅手动环境需要）

使用 `environment.yml` 创建环境时可跳过本步；如果是手动创建环境，则执行：

```bash
cd monitor-server
pip install -r requirements.txt
```

### 3. 安装 DEBUG_WEB_STREAM 依赖（可选）

仅当需要 `DEBUG_WEB_STREAM=true` 并启动本地 RTMP 靶子时需要：

```bash
cd tools
npm install node-media-server
cd ..
```

### 4. 检查环境

```bash
python -c "import fastapi, sqlalchemy, pytest; print('python deps ok')"
ffmpeg -version
node -v
```

### 5. 配置环境变量

`.env` 已提供默认值，按需修改：

```bash
# 数据库（默认 SQLite，可改为 PostgreSQL / MySQL）
DATABASE_URL=sqlite:///./monitor.db

# 监听地址
HOST=0.0.0.0
PORT=8000

# Raw RTMP readiness probe
STREAM_READY_TIMEOUT=30
STREAM_PROBE_TIMEOUT=8
STREAM_READY_INTERVAL=1
```

### 6. 启动服务

```bash
# 开发模式（自动 reload）
python -m src.run

# 或直接调用 uvicorn
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

### 7. 验证

| 端点 | 地址 |
|---|---|
| Health Check | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

### 8. 运行测试

```bash
pytest src/tests/ --tb=short
```

---

## Docker 部署

```bash
docker-compose -f docker-compose.prod.yml up -d
```

服务暴露在 `:80`（nginx → app:8000）。

---

## 开发约定

### 分层架构（详见 `openspec/specs/`）

| 层 | 目录 | 职责 | 规范 |
|---|---|---|---|
| 网络层 | `src/network/api/` | HTTP Router，调 `service/*_task.py` | `network-layer` |
| | `src/network/wss/` | WebSocket 端点，被 service 调取 | |
| | `src/network/rtmp/` | RTMP 地址构建 | |
| 业务层 | `src/service/*_task.py` | 门户函数，编排业务流程 | `service-layer` |
| | `src/service/*_module/` | 内部逻辑包，一个 task 对应一个 module | |
| 数据层 | `src/repository/` | BaseRepo 泛型基类，每模型一个 Repo | `repo-base` |
| 模型层 | `src/models/` | SQLAlchemy 模型，继承 `extensions.Base` | 各 model spec |
| Schema层 | `src/schema/http/` | REST 请求/响应 → Swagger 自动渲染 | `schema-convention` |
| | `src/schema/wss/` | WSS 命令协议 → Pydantic + markdown | |

### 代码约定

- 占位文件 SHALL 在顶部包含中文 docstring 说明模块预期职责
- Router 不直接操作数据库，通过 `service/*_task.py` 调用
- 数据库会话通过 `db: Session` 参数注入（FastAPI `Depends(get_db)`）
- `*_task.py` 不持有全局连接，不直接操作网络层

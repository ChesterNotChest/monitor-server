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

### 1. 创建 & 激活环境

```bash
conda create -n monitor python=3.12 -y
conda activate monitor
```

### 2. 安装依赖

```bash
cd monitor-server
pip install -r requirements.txt
```

### 3. 配置环境变量

`.env` 已提供默认值，按需修改：

```bash
# 数据库（默认 SQLite，可改为 PostgreSQL / MySQL）
DATABASE_URL=sqlite:///./monitor.db

# 监听地址
HOST=0.0.0.0
PORT=8000
```

### 4. 启动服务

```bash
# 开发模式（自动 reload）
python -m src.run

# 或直接调用 uvicorn
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 验证

| 端点 | 地址 |
|---|---|
| Health Check | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

### 6. 运行测试

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

- **路由** → `src/api/`，每个模块一个 Router，在 `app.py` 中注册
- **模型** → `src/models/`，继承 `src.extensions.Base`
- **业务** → `src/service/`，一个 task 对应一个子包
- **数据库会话** → `Depends(get_db)` 注入

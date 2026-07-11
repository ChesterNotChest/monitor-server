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
│   ├── api/                # 路由层（FastAPI Router）
│   ├── models/             # SQLAlchemy 数据模型
│   ├── schema/             # Pydantic 请求 / 响应模型
│   ├── service/            # 业务逻辑层
│   ├── repository/         # 数据仓库层
│   └── tests/              # 测试
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

## Docker / Jenkins CD 部署

生产部署由 Jenkins 构建 `monitor-server:${BUILD_NUMBER}`，再用 `docker compose up -d --remove-orphans` 长期运行。MySQL 是独立的长期容器，不放进 Jenkins 反复重建。

### 1. MySQL 容器

当前推荐的 MySQL 容器配置：

```bash
docker run -d \
  --name monitor-mysql \
  --restart unless-stopped \
  --network servercicd_default \
  -p 127.0.0.1:3676:3306 \
  -v /home/liusu/mysql-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD='你的root密码' \
  -e MYSQL_DATABASE=monitor \
  -e MYSQL_USER=monitor \
  -e MYSQL_PASSWORD='monitor_placeholder2026' \
  mysql:8.4 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci
```

端口只绑定宿主机回环地址，服务器本机可用 `127.0.0.1:3676` 连接；外部机器不能直接用服务器 IP 访问。`monitor-app` 容器通过 Docker 网络访问 `monitor-mysql:3306`。

### 2. 模型挂载

Jenkins 参数 `MODEL_DIR` 默认：

```text
/home/liusu/video/models
```

生产 compose 会把它只读挂载到容器内：

```text
/app/src/third-party
```

因此 YOLO 权重至少需要存在于：

```text
/home/liusu/video/models/yolo/yolo11n.pt
```

容器内对应路径：

```text
/app/src/third-party/yolo/yolo11n.pt
```

### 3. Jenkins 参数

Jenkins 任务使用 `Build with Parameters`，生产部署时设置：

```text
DEPLOY_PROD=true
HTTP_PORT=8081
RTMP_PORT=1935
STREAM_HTTP_PORT=8082
SRS_API_PORT=1985
SRS_RTC_PORT=8000
SRS_CANDIDATE=10.126.59.25
SRS_PUBLIC_HOST=10.126.59.25
MODEL_DIR=/home/liusu/video/models
DATABASE_URL=mysql+pymysql://monitor:monitor_placeholder2026@monitor-mysql:3306/monitor?charset=utf8mb4
JWT_SECRET=换成生产随机长字符串
RUN_SEED_DATA=false
```

首次需要写入业务枚举和告警规则时，可以临时设置 `RUN_SEED_DATA=true`。应用启动时会自动建表并创建默认管理员；`RUN_SEED_DATA` 只用于额外业务种子数据。

### 4. 部署后验证

```bash
docker ps --filter name=monitor-mysql
docker ps --filter name=monitor-app
curl --noproxy '*' http://127.0.0.1:8081/health
docker exec monitor-app find /app/src/third-party -maxdepth 3 -type f
docker exec monitor-app ls -lah /app/face_images
```

`monitor-node` 联调配置示例：

```env
SERVER_BASE_URL=10.126.59.25
WSS_SCHEME=ws
WSS_PORT=8081
RTMP_PORT=1935
DEBUG_WSS=false
RTMP_DEBUG=false
SECRET_KEY=节点token
```

---

## 开发约定

- **路由** → `src/api/`，每个模块一个 Router，在 `app.py` 中注册
- **模型** → `src/models/`，继承 `src.extensions.Base`
- **业务** → `src/service/`，一个 task 对应一个子包
- **数据库会话** → `Depends(get_db)` 注入
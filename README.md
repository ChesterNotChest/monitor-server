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

`environment.yml` 是唯一的环境描述文件，涵盖核心监控和 AI 识别全部依赖。

### 1. 创建 & 激活环境

```bash
cd monitor-server
conda env create -f environment.yml
conda activate monitor-server
```

该环境会安装：

- `python=3.12`
- `ffmpeg`：Server 侧拉取 audio/video 并合并推流
- `nodejs`：`DEBUG_WEB_STREAM=true` 时启动本地 RTMP 靶子
- `dlib`（conda-forge 预编译）：人脸检测，Windows 无编译问题
- 其余 Python 依赖（fastapi、sqlalchemy、torch、ultralytics 等）通过 pip

如果环境已存在，可更新：

```bash
conda env update -f environment.yml --prune
conda activate monitor-server
```

环境创建后，`face_recognition` 需额外手动安装（pip 不认 conda 已装的 dlib，会尝试拉取 dlib 源码并编译失败）。`--no-deps` 跳过 dlib 重装，`face_recognition_models` 也需一同安装：

```bash
conda activate monitor-server
pip install --no-deps face_recognition_models face_recognition
```

> **Windows 注意**：`dlib` 通过 conda-forge 预编译安装，无需 CMake 或 Visual Studio Build Tools。`face_recognition` 用 `--no-deps` 跳过 pip 对 dlib 的重复拉取。

### 2. 仅安装核心依赖（如不需要 AI 模块）

如果暂时不需要 AI 识别能力，可手动创建精简环境：

```bash
conda create -n monitor-server python=3.12 ffmpeg nodejs -c conda-forge
conda activate monitor-server
pip install fastapi uvicorn[standard] sqlalchemy pydantic-settings python-multipart pytest pytest-asyncio httpx python-jose[cryptography] bcrypt
```

后续需要 AI 时再补：

```bash
conda install -c conda-forge dlib
pip install --no-deps face_recognition_models face_recognition
pip install ultralytics opencv-python-headless torch torchaudio tensorflow-hub tensorflow torchvision pytorchvideo "setuptools<70"
```

### 3. 安装 DEBUG_WEB_STREAM 依赖（可选）

仅当需要 `DEBUG_WEB_STREAM=true` 并启动本地 RTMP 靶子时需要：

```bash
# 在仓库根目录执行
cd tools
npm install
cd ..
```

### 4. 下载 AI 模型权重（如不需要智能分析可跳过）

```bash
cd monitor-server
python src/third-party/download_weights.py
```

脚本会自动下载并跳过已存在的文件，可放心重复运行。首次下载约 460 MB。

### 5. 检查环境

```bash
# 核心依赖
python -c "import fastapi, sqlalchemy, pytest; print('python deps ok')"
ffmpeg -version

# Debug 靶子（可选）
node -v && cd tools && node -e "require('node-media-server')" && cd ..
```

### 6. 配置环境变量

`.env` 已提供默认值，按需修改：

```bash
# ── 数据库 ──
DATABASE_URL=sqlite:///./monitor.db

# ── 监听地址 ──
HOST=0.0.0.0
PORT=8000

# ── RTMP (SRS) ──
RTMP_HOST=127.0.0.1
RTMP_PORT=1935
RTMP_DEBUG=true

# ── SRS ──
SRS_HOST=127.0.0.1
SRS_RTMP_PORT=1935
SRS_HTTP_PORT=8082

# ── WSS (Node) ──
WSS_NODE_PORT=9000
WSS_NODE_DEBUG=false

# ── Debug ──
DEBUG_WEB_STREAM=false
```

### 7. 启动服务

```bash
# 开发模式（自动 reload）
python -m src.run

# 或直接调用 uvicorn
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

### 8. 验证

| 端点 | 地址 |
|---|---|
| Health Check | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

### 9. 运行测试

```bash
pytest src/tests/ --tb=short
```

---

## Docker 部署

### 1. 准备模型权重

```bash
# 首次：下载模型权重到宿主机目录
mkdir -p ./models
cd monitor-server/src/third-party && python download_weights.py
cp -r monitor-server/src/third-party/* ./models/
```

### 2. 启动服务

```bash
docker-compose -f docker-compose.prod.yml up -d
```

模型目录通过 `${MODEL_DIR:-./models}` 挂载到容器 `/app/src/third-party/`。权重文件只需下载一次，后续重启无需重新下载。

服务暴露在 `:80`（nginx → app:8000）。

---

## 认证

### 默认管理员

首次启动时自动生成管理员账户，密码写入 `monitor-server/admin_password.txt`。

```
POST /api/v1/auth/login  →  {access_token, user}
 GET /api/v1/auth/me     →  当前用户信息
```

### 角色与权限

| 角色 | 标识 | 权限范围 |
|------|------|----------|
| 安全员 | `security_guard` | 仪表板、监控、告警处理、电子围栏 |
| 负责人 | `manager` | 安全员权限 + 枚举管理、异常/告警分级、报表、命名人物查看 |
| 运维员 | `operator` | 仪表板、告警查看、设备管理、系统日志、用户管理、异常/告警分级 |

所有受保护端点需在请求头携带 `Authorization: Bearer <access_token>`。

---

## AI 模型安装

智能分析模块依赖以下模型，存放于 `src/third-party/`。Python 依赖由 `environment.yml` 统一管理，模型权重文件需额外下载。

### 下载模型权重

```bash
conda activate monitor-server
cd monitor-server
python src/third-party/download_weights.py
```

脚本会自动下载以下权重并跳过已存在的文件（可重复运行）：

| 模型 | 文件 | 大小 | 说明 |
|------|------|------|------|
| YOLO11 | `yolo/yolo11n.pt` | ~5 MB | 目标检测 / 跟踪（nano 版） |
| SlowFast (Kinetics) | `slowfast/SLOWFAST_8x8_R50.pkl` | ~140 MB | 场景级行为分类 |
| SlowFast (AVA) | `slowfast/SLOWFAST_8x8_R50_DETECTION.pyth` | ~258 MB | 人物级动作检测 60 类 |
| YAMNet | `yamnet/yamnet_tfhub/` | ~55 MB | AudioSet 521 类音频分类 |
| face_recognition | 随包内置 | — | 无需单独下载 |

### 模型清单

| 模型 | 版本 | 安装方式 | 用途 |
|------|------|----------|------|
| YOLO11 | ≥8.3.0 | `pip install ultralytics>=8.3.0` | 目标检测 / 跟踪 / 分割 |
| Dlib | ≥19.24 | `conda install -c conda-forge dlib` | HOG + CNN 人脸检测，68 点 landmark |
| face_recognition | ≥1.3.0 | `pip install --no-deps face_recognition_models face_recognition` | dlib wrapper，128D 人脸特征向量 |
| SlowFast (Kinetics) | R-50 | `pip install pytorchvideo>=0.1.5` | 场景级行为分类（打架/跌倒/奔跑等） |
| SlowFast (AVA) | R-50 | pytorchvideo 内置 | 人物级动作检测：抽烟/打电话/喝水等 60 类 |
| YAMNet | torchaudio 内置 | 随 `torchaudio>=2.1.0` 安装 | AudioSet 521 类音频分类 |
| OpenCV | ≥4.10 | `pip install opencv-python-headless>=4.10` | 帧解码 / 预处理 / 标注叠加 |

> **注意**：`dlib` 通过 conda-forge 预编译安装（Windows 无需 CMake）。`setuptools` 需 <70 版本（`face_recognition_models` 依赖 `pkg_resources`）。CD 部署时 `src/third-party/` 挂载为宿主机路径，权重文件一次下载、容器重启不丢失。

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

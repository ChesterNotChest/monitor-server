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

`environment.yml` 是唯一的环境描述文件。

### 1. 创建 & 激活环境

```bash
cd monitor-server
conda env create -f environment.yml
conda activate monitor-server
```

环境已存在时更新：

```bash
cd monitor-server
conda env update -f environment.yml --prune
conda activate monitor-server
```

CUDA 版 PyTorch 需走 PyTorch 官方源安装（国内镜像不含 CUDA wheel）：

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
```

> **为什么必须 `--force-reinstall`**：`tensorflow` 依赖的 CUDA DLL 版本与 PyTorch 冲突。
> `conda env update` 装 TF 时会覆盖 `Library/bin` 下的 CUDA 运行时，导致 `torch.cuda.is_available()` 返回 `False`。
> 两个框架共用 CUDA DLL 是 Windows conda+pip 混装环境的结构性冲突——**后装的赢，需要手动修回来**。
> environment.yml 已包含 `conda-forge::cudnn` 防止 `--prune` 删除，但 TF 仍可能覆盖其他 DLL。

`face_recognition` 依赖 conda 预装的 `dlib`，需手动补装（pip 不认 conda 包）：

```bash
pip install --no-deps face_recognition_models face_recognition
```

> **Windows 注意**：`dlib` 通过 conda-forge 预编译安装，无需 CMake 或 Visual Studio Build Tools。

### 1.1 快速诊断 CUDA 可用性

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
# 预期: CUDA: True
# 若 False → 重跑 CUDA 版 PyTorch 安装命令 + 确认 cudnn 存在:
#   ls E:/Miniconda3/envs/monitor-server/Library/bin/cudnn*
```

### 2. 安装 Node.js RTMP 靶子依赖

```bash
cd monitor-server/tools
npm install
cd ../..
```

```bash
cd monitor-node/rtmp_server
npm install
cd ../..
```

### 3. 下载 AI 模型权重

```bash
cd monitor-server
python src/third-party/download_weights.py
```

首次下载约 460 MB，已存在的文件自动跳过。

### 3b. SRS（Web 端联调用）

Web 前端需要 WebRTC 拉流时运行：

```bash
bash srs/setup.sh
```

自动下载 Windows 二进制或使用 Docker 启动 SRS，监听 :1935（RTMP）、:8080（HTTP-FLV）、:8000（WebRTC）。配置见 `srs/srs.conf`。

### 4. 检查环境

```bash
# 核心依赖
python -c "import fastapi, sqlalchemy, pytest; print('python deps ok')"
ffmpeg -version

# 计算机视觉
python -c "import cv2; print('cv2 ok')"

# 人脸识别
python -c "import face_recognition; print('face_recognition ok')"

# Node.js 靶子
node -e "require('node-media-server'); print('node-media-server ok')"
```

### 5. 配置环境变量

`.env` 已提供默认值，按需修改：

```bash
DATABASE_URL=sqlite:///./monitor.db
HOST=0.0.0.0
PORT=8000
RTMP_HOST=127.0.0.1
RTMP_PORT=1935
RTMP_DEBUG=true
SRS_HOST=127.0.0.1
SRS_RTMP_PORT=1935
SRS_HTTP_PORT=8082
WSS_NODE_PORT=9000
WSS_NODE_DEBUG=false
DEBUG_WEB_STREAM=false
```

### 6. 启动服务

```bash
python -m src.run
```

### 7. 验证

| 端点 | 地址 |
|---|---|
| Health Check | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |

### 8. 运行测试

```bash
pytest src/tests/ --tb=short
```

### 9. 端到端视觉验证

本地无需 SRS 或 Docker——三终端架构，Node 按需推流。

详见 `openspec/specs/local-dev-e2e-paradigm/spec.md`。

**模式一（快速验证）：Node 独奏推流**

```bash
cd monitor-node
set RTMP_DEBUG=true
set DEBUG_WSS=true
python run.py
# → VLC 打开日志中打印的拉流地址（如 rtmp://127.0.0.1:1935/live/USB_webcam_video_0）
```

**模式二（标准联调）：Node + Server + RTMP 服务器**

```bash
# Terminal 0 — RTMP 中转（二选一）
cd monitor-node/rtmp_server && node index.js          # 纯 RTMP
# 或 .\srs-bin\srs.exe -c srs\srs.conf                # 含 WebRTC

# Terminal 1 — Node（等待 Server 命令）
cd monitor-node
set RTMP_DEBUG=false
set DEBUG_WSS=false
set SERVER_BASE_URL=127.0.0.1
set WSS_PORT=8000
python run.py

# Terminal 2 — Server（拉流+AI）
cd monitor-server
set DEBUG_WEB_STREAM=true
set RTMP_DEBUG=true
python -m src.run

# 创建 View 触发推流（Server 通过 WSS 命令 Node 启动设备流）
curl -X POST http://127.0.0.1:8000/api/v1/views/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"video_id":1,"audio_id":1}'

# Terminal 3 — 播放标注流
# VLC 打开响应中的 rtmp_url（如 rtmp://127.0.0.1:1936/view/1）
```

> 三个进程均支持 `CTRL+C` 停止。Terminal 0 的 RTMP 服务器由 `node-media-server` 实现，Terminal 1 Node 不自动推流，由 Server 通过 WSS `UPDATE_STREAM` 命令按需启动。

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
| 负责人 | `manager` | 仪表板、监控、告警处理、枚举管理、异常/告警分级、报表、系统日志、用户管理 |
| 运维员 | `operator` | **全部权限**（技术管理员：设备管理、系统日志、用户管理、枚举管理、告警处理、电子围栏、报表等） |

所有受保护端点需在请求头携带 `Authorization: Bearer <access_token>`。

---

## AI 模型参考

所有 AI 模型权重存放于 `src/third-party/`，通过 `download_weights.py` 一键下载（见上方「Miniconda 部署 → 步骤 3」）。Python 依赖由 `environment.yml` 统一管理。

### 模型清单与权重文件

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

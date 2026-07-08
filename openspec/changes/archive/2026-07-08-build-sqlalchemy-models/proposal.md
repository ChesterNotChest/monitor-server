## Why

监控服务需要一套完整的数据模型来支撑计算机节点管理、音视频采集设备关联、异常检测与响应流程。当前 `src/models/` 仅有 `example.py` 模板，缺少业务模型定义，无法进行数据库初始化与业务开发。

## What Changes

- 新增 13 个 SQLAlchemy 数据模型类，每个模型一个独立文件，遵循项目现有的 `Base` + `DeclarativeBase` 范式
- 新增全局枚举常量（YOLO 实体类型、SlowFast 行为类型、YAMNet 声音类型、异常严重级别、响应动作类型）
- 定义多对多关联表（异常-实体、异常-行为、异常-声音），支持异常与多种 AI 检测结果的灵活关联
- 每个模型文件包含完整的字段定义、外键约束、索引及 `__repr__` 方法

## Capabilities

### New Capabilities

- `computer-node-model`: 计算机节点表，记录注册节点的 ID 与认证 Token
- `video-device-model`: 视频采集设备表，关联所属计算机节点
- `audio-device-model`: 音频采集设备表，关联所属计算机节点
- `monitor-view-model`: 监控视图表，组合视频与音频设备，记录缓存路径
- `electronic-fence-model`: 电子围栏表，存储区域坐标数据
- `entity-enum-model`: 实体类型枚举表，对应 YOLO 目标检测的实体类别
- `action-enum-model`: 人物行为枚举表，对应 SlowFast 行为识别类别
- `sound-enum-model`: 声音状态枚举表，对应 YAMNet 音频分类类别
- `named-person-model`: 命名人物表，关联头像路径与面部特征向量 JSON
- `exception-model`: 异常枚举表，定义异常严重级别与分组，支持后续触发条件扩展
- `alert-group-model`: 告警级别分组表
- `response-enum-model`: 响应动作枚举表，定义触发录制、发送通知等动作，预留状态机扩展
- `situation-event-model`: 事件表，关联监控视图与异常，记录发生的异常事件

### Modified Capabilities

_无_（纯新增数据模型，不修改现有功能）

## Impact

- 影响范围：`src/models/`（新增 13+ 文件）、`src/constants.py`（新增枚举类）、`src/extensions.py`（无需修改，使用现有 `Base`）
- 依赖：`SQLAlchemy`、`sqlite`（开发阶段）/ `PostgreSQL`（生产阶段）
- 后续依赖本模型的模块：`src/repository/`、`src/service/`、`src/api/`

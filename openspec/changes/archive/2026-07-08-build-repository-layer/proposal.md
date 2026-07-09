## Why

13 个数据模型已就绪但缺少统一的数据访问层。随着人脸识别、区域检测、告警处置、日志回放等模块的逐步建设（8 大系统模块、50+ 预期模型），需要一个可扩展的类式 Repository 基类来消除 CRUD 样板代码、统一分页/排序/过滤行为，并支持两人并行分工开发。

## What Changes

- 新增 `src/repository/base.py` — 泛型 `BaseRepo[T]` 基类，封装通用 CRUD + 分页 + 存在性检查 + 批量操作
- 新增 **组 A（基础设备管理）** 7 个 Repository 类：NodeRepo、VideoDeviceRepo、AudioDeviceRepo、MonitorViewRepo、ElectronicFenceRepo、EntityTypeRepo、ActionTypeRepo、SoundTypeRepo
- 新增 **组 B（人员/告警/事件）** 5 个 Repository 类：NamedPersonRepo、AlertGroupRepo、ExceptionDefRepo、ResponseActionRepo、SituationEventRepo
- MonitorViewRepo 包含 View 创建/删除时的流状态推导逻辑：`in_use()` 检查设备是否被其他 View 引用、`delete` 后自动判断释放
- 不修改 models，不创建 service/api/schema 层代码（但 Repository 接口预留了 service 层所需的查询语义）

## Capabilities

### New Capabilities

- `repo-base`: 泛型基类 `BaseRepo[T]`，提供 `get`/`all`/`create`/`delete`/`count`/`exists`/`paginate` 通用方法
- `repo-group-a-device`: 组 A — 设备管理相关 Repository（Node、VideoDevice、AudioDevice、MonitorView、ElectronicFence、EntityType、ActionType、SoundType）
- `repo-group-b-alert`: 组 B — 人员/告警/事件相关 Repository（NamedPerson、AlertGroup、ExceptionDef、ResponseAction、SituationEvent）

### Modified Capabilities

_无_（纯新增 Repository 层，不修改现有模型或配置）

## Impact

- 新增文件：`src/repository/base.py` + 13 个 `*_repo.py` 文件
- 影响范围：仅 `src/repository/` 目录，不修改 `src/models/`、`src/extensions.py`、`src/constants.py`
- 依赖：`sqlalchemy`（已在 `requirements.txt` 中）、现有 `src.models.*`
- 为后续 service 层（`src/service/`）、API 层（`src/api/`）提供数据访问基础

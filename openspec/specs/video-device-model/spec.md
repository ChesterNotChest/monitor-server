# Video Device Model

**Purpose:** 定义视频采集设备数据模型，记录设备信息、所属计算节点及推流状态。设备名称在单个 Node 下唯一，不同 Node 可有同名设备。

## Requirements

### Requirement: 视频采集设备表定义
系统 SHALL 定义 `VideoDevice` 模型，映射到 `video_devices` 表，记录视频采集设备信息及其所属节点。

- `id`: 自增主键（Integer）
- `name`: 设备名称（String，非空）
- `node_id`: 外键关联 `nodes.id`（Integer，非空，索引）
- `streaming`: 推流状态（Boolean，默认 false）
- `created_at`: 创建时间（DateTime，server_default）
- 唯一约束：`(node_id, name)` 联合唯一（不同 Node 可有同名设备，同一 Node 下设备名不可重复）

#### Scenario: 关联视频设备到节点
- **WHEN** 插入视频设备记录并指定 `node_id`
- **THEN** 系统建立设备与节点的外键关联，可通过 `node_id` 查询该节点下所有视频设备

#### Scenario: 删除节点时级联处理
- **WHEN** 删除某个计算机节点
- **THEN** 系统拒绝删除（外键约束保护），需先解除或删除关联视频设备

#### Scenario: 不同 Node 下可使用同名设备
- **WHEN** Node A 和 Node B 各自上报名为 "cam0" 的视频设备
- **THEN** 系统允许两条记录共存，因为 (node_id, name) 组合不同

#### Scenario: 同一 Node 下设备名不可重复
- **WHEN** Node A 上报两个名为 "cam0" 的视频设备
- **THEN** 系统拒绝第二条记录插入（联合唯一约束保护）

#### Scenario: 推流状态更新
- **WHEN** Node 响应 `UPDATE_STREAM enable=true` 成功后
- **THEN** 系统更新对应 VideoDevice 的 `streaming=true`

#### Scenario: 停止推流状态更新
- **WHEN** Node 响应 `UPDATE_STREAM enable=false` 成功后
- **THEN** 系统更新对应 VideoDevice 的 `streaming=false`

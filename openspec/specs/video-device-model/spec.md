# Video Device Model

**Purpose:** 定义视频采集设备数据模型，记录设备信息及其所属计算节点。

## Requirements

### Requirement: 视频采集设备表定义
系统 SHALL 定义 `VideoDevice` 模型，映射到 `video_devices` 表，记录视频采集设备信息及其所属节点。

- `id`: 自增主键（Integer）
- `name`: 设备名称（String，唯一，非空）
- `node_id`: 外键关联 `nodes.id`（Integer，非空，索引）

#### Scenario: 关联视频设备到节点
- **WHEN** 插入视频设备记录并指定 `node_id`
- **THEN** 系统建立设备与节点的外键关联，可通过 `node_id` 查询该节点下所有视频设备

#### Scenario: 删除节点时级联处理
- **WHEN** 删除某个计算机节点
- **THEN** 系统拒绝删除（外键约束保护），需先解除或删除关联视频设备

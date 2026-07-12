# Computer Node Model

**Purpose:** 定义计算机节点数据模型，记录接入监控系统的注册节点标识、认证凭据与 WSS 连接状态。

## Requirements

### Requirement: 计算机节点表定义
系统 SHALL 定义 `Node` 模型，映射到 `nodes` 表，记录接入监控系统的计算机节点信息。

- `id`: 自增主键（Integer）
- `token`: 节点认证令牌（String，唯一，非空，索引）
- `is_connected`: WSS 连接状态（Boolean，默认 false）
- `last_seen`: 最后活跃时间（DateTime，可空）
- `created_at`: 创建时间（DateTime，server_default）

#### Scenario: 注册新节点
- **WHEN** 向 `nodes` 表插入一条记录，提供 `token`
- **THEN** 系统成功持久化该节点，自动生成 `id`，`is_connected` 默认为 false，`last_seen` 为 NULL

#### Scenario: 按 token 查找节点
- **WHEN** 通过 `token` 值查询 `nodes` 表
- **THEN** 系统利用索引快速返回对应节点记录

#### Scenario: Node 连接后更新状态
- **WHEN** Node 通过 WSS 成功连接并认证
- **THEN** 系统更新该 Node 记录的 `is_connected=true`、`last_seen=NOW()`

#### Scenario: Node 断开后更新状态
- **WHEN** Node 的 WSS 连接断开
- **THEN** 系统更新该 Node 记录的 `is_connected=false`、`last_seen=NOW()`

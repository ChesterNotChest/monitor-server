# Computer Node Model

**Purpose:** 定义计算机节点数据模型，记录接入监控系统的注册节点标识与认证凭据。

## Requirements

### Requirement: 计算机节点表定义
系统 SHALL 定义 `Node` 模型，映射到 `nodes` 表，记录接入监控系统的计算机节点信息。

- `id`: 自增主键（Integer）
- `token`: 节点认证令牌（String，唯一，非空，索引）

#### Scenario: 注册新节点
- **WHEN** 向 `nodes` 表插入一条记录，提供 `token`
- **THEN** 系统成功持久化该节点，自动生成 `id`

#### Scenario: 按 token 查找节点
- **WHEN** 通过 `token` 值查询 `nodes` 表
- **THEN** 系统利用索引快速返回对应节点记录

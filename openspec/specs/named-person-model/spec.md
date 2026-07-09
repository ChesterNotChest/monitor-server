# Named Person Model

**Purpose:** 定义命名人物数据模型，关联人脸头像与面部特征向量，用于人员识别。

## Requirements

### Requirement: 命名人物表定义
系统 SHALL 定义 `NamedPerson` 模型，映射到 `named_persons` 表，存储已命名人员的信息及其面部特征向量引用。

- `id`: 自增主键（Integer）
- `name`: 人物姓名（String 128，唯一非空），作为业务标识
- `avatar_path`: 头像文件相对路径（String 512，可空）
- `feat_json_id`: 面部特征向量 JSON 文件引用（String 256，可空）
- `created_at`: 创建时间（DateTime，服务器默认当前时间）

#### Scenario: 注册命名人物
- **WHEN** 插入记录提供 `name`，可选提供 `avatar_path` 和 `feat_json_id`
- **THEN** 系统持久化该人物信息

#### Scenario: 查询命名人物
- **WHEN** 查询 `named_persons` 全表
- **THEN** 系统返回所有已注册的命名人物列表，包含姓名、头像路径与特征向量引用

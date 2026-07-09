# User Model

**Purpose:** 定义 User 最小模型（username + role），供日志和告警处置共用。

## Requirements

### Requirement: User 模型定义
系统 SHALL 定义 `User` 模型，映射到 `users` 表，存储系统用户的基本信息。

- `id`: 自增主键
- `username`: 用户名（String 64，唯一非空）
- `role`: 角色枚举（UserRole IntEnum：SECURITY=1 / ADMIN=2 / MANAGER=3 / OPERATOR=4）
- `created_at`: 创建时间

#### Scenario: 创建用户
- **WHEN** 插入记录提供 username 和 role
- **THEN** 系统持久化该用户信息

#### Scenario: 查询用户列表
- **WHEN** 查询 users 全表
- **THEN** 系统返回所有已注册用户

#### Scenario: 用户名唯一约束
- **WHEN** 尝试创建重复 username
- **THEN** 系统拒绝并返回冲突错误

### Requirement: User CRUD API
系统 SHALL 提供 User 的基本管理 API。

#### Scenario: 创建用户
- **WHEN** 客户端 `POST /api/v1/users` 请求体 `{"username": "张安保", "role": 1}`
- **THEN** 系统创建用户，返回 201

#### Scenario: 查询用户列表
- **WHEN** 客户端 `GET /api/v1/users`
- **THEN** 系统返回所有用户列表

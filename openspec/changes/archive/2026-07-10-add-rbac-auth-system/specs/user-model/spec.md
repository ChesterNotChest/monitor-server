## ADDED Requirements

### Requirement: User 模型定义
系统 SHALL 定义 `User` 模型映射到 `users` 表，存储用户认证信息与角色。

- `id`: 自增主键
- `username`: 用户名（String，唯一，非空，索引）
- `password_hash`: bcrypt 密码哈希（String，非空）
- `role`: 角色标识（String，非空，取值 security_guard / manager / operator）
- `is_active`: 账户启用状态（Boolean，默认 true）
- `created_at`: 创建时间（DateTime，server_default）

#### Scenario: 创建用户
- **WHEN** 向 `users` 表插入记录
- **THEN** 密码以 bcrypt hash 形式存储，role 为三种有效值之一

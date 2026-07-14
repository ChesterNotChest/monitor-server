## ADDED Requirements

### Requirement: Env-based default API key
系统 SHALL 从 `.env` 读取 `DEEPSEEK_API_KEY` 作为日报 AI 洞察的默认密钥。

- 配置项：`DEEPSEEK_API_KEY`（可选，为空字符串时 AI 洞察不可用）
- 配置项：`DEEPSEEK_REPORT_MODEL`（默认 `deepseek-v4-flash`）
- `.env.example` SHALL 包含这两个字段及注释说明

#### Scenario: Key configured
- **WHEN** `.env` 中 `DEEPSEEK_API_KEY` 有值
- **THEN** 定时生成的日报自动调用 DeepSeek 产生洞察层

#### Scenario: Key not configured
- **WHEN** `.env` 中 `DEEPSEEK_API_KEY` 为空
- **THEN** 日报仅包含统计层，洞察层区域显示"请配置 API Key"

### Requirement: User-overridable API key
系统 SHALL 允许用户在前端手动输入 DeepSeek API Key，覆盖 env 默认值。

- API 端点 `PUT /api/v1/reports/settings/` 接收 `{ "api_key": "sk-xxx", "model": "deepseek-v4-flash" }`
- 前端在日报页面提供 settings 入口（齿轮图标），弹窗输入 key + model
- 用户输入的值保存到 `report_settings` 表或本地 localStorage，优先于 env 默认值

#### Scenario: User enters custom key
- **WHEN** 用户输入 API key 并保存
- **THEN** 后续手动/自动生成的日报使用用户的 key 调用 DeepSeek

#### Scenario: User clears custom key
- **WHEN** 用户清空 API key 设置
- **THEN** 系统回退使用 env 默认 key（如有），否则仅统计层可用

### Requirement: Key security
系统 SHALL 不在 API 响应中暴露完整的 API Key。

- `GET /api/v1/reports/settings/` 仅返回 key 的脱敏版本（如 `sk-xxx...abc` 前后各 6 位 + `****` 中间）
- 前端设置页显示已配置 key 的脱敏版本，允许重新输入覆盖

#### Scenario: Retrieve current key status
- **WHEN** 用户查看 API Key 设置
- **THEN** 返回 `{ "has_key": true, "key_preview": "sk-1234****abcd", "model": "deepseek-v4-flash", "source": "env" | "user" }`

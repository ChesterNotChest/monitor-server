# Alert Cooldown Config

## Purpose

用户可以为一组异常规则设置自定义冷却时间（秒），替代全局 `ALERT_COOLDOWN` 默认值。

## ADDED Requirements

### Requirement: ExceptionDef has cooldown_seconds

`ExceptionDef` 模型 SHALL 包含 `cooldown_seconds` 字段，默认值为 `ALERT_COOLDOWN`（30秒）。
API 创建/更新异常规则时 SHALL 接受可选的 `cooldown_seconds` 参数。

#### Scenario: Custom cooldown via API

- **WHEN** 用户通过 API 创建 ExceptionDef 并设置 `cooldown_seconds=60`
- **THEN** 该规则的告警冷却时间为 60 秒

#### Scenario: Default cooldown

- **WHEN** 用户创建 ExceptionDef 不设置 `cooldown_seconds`
- **THEN** 使用全局默认值 30 秒

# Schema Convention (Delta)

## ADDED Requirements

### Requirement: HTTP schema fields carry descriptions

`schema/http/` 下的所有 Pydantic Field SHALL 包含 `description` 参数。此要求适用于请求体字段和响应体字段。description SHALL 使用中文，SHALL 描述字段含义、取值范围（如有）、默认值（如有）。

#### Scenario: Field without description is a review failure

- **WHEN** 审查发现 `schema/http/` 中某 Field 缺少 `description`
- **THEN** 该 Field SHALL 在 PR 合入前补充 description

#### Scenario: Description remains visible in OpenAPI

- **WHEN** 带有 `Field(description="...")` 的 Pydantic 模型被用作 FastAPI 响应模型
- **THEN** Swagger 自动展示该 description 作为字段说明

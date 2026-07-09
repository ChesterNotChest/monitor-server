# E2E Tests

## Purpose
端到端测试：启动完整 FastAPI 服务（TestClient），覆盖完整 HTTP 请求 → 路由 → Service → Repository → 数据库 → 响应的链路。

## When to use
- 验证完整的用户操作流程（如：创建 View → 触发告警 → 推送通知）
- API 契约验证
- 与其他模块（如 WebSocket、外部 AI 服务）的集成验证

## How to run
```bash
# 需要项目依赖全部安装
pytest tests/e2e/ -v

# 带覆盖率
pytest tests/e2e/ -v --cov=src --cov-report=term-missing
```

## Differences from unit/integration tests
| Layer | Scope | DB |
|---|---|---|
| Unit (smoke) | Single Repo class | Transaction rollback |
| Integration | Multiple Repos collaborating | Transaction rollback |
| E2E | Full HTTP request chain | Real SQLite file |

## Current status
E2E tests will be added as Service and API layers are built.

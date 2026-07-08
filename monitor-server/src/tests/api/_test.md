# API Tests (预留)

API 层测试将在对应路由实现后添加。

Expected structure:
- `tests/api/test_*_routes.py` for each router module

Rules:
- Use FastAPI TestClient for request simulation
- Mock Service layer via dependency overrides
- Test request validation, status codes, response schemas
- Test error responses (404, 422, 500)

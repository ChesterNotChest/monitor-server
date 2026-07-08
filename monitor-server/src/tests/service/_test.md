# Service Tests (预留)

Service 层测试将在对应 Service 类实现后添加。

Expected structure:
- `tests/service/test_*_service.py` for top-level services
- `tests/service/<module>/test_*.py` for sub-module services

Rules:
- Mock Repository layer (inject mock repos via constructor)
- Test business logic, validation, error handling
- Use real db session for integration-style service tests when needed

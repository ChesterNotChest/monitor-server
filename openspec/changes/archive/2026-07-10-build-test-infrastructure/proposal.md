## Why

当前仅有 `/health` 一个 pytest 用例和一份组 A 的临时冒烟脚本（`_smoke_test.py`），组 B 的 5 个 Repository（NamedPerson、AlertGroup、ExceptionDef、ResponseAction、SituationEvent）完全无测试覆盖。异常路径（FK 约束冲突、unique 重复、空值边界）零覆盖。缺乏统一的测试目录规范和 CI 架构，后续 service/api/e2e 层的测试将无处安放。

## What Changes

- 建立 **测试目录组织规范**，写入 `openspec/specs/` 作为项目标准
  - `tests/<package>/` 镜像源码包结构：`tests/repository/`、`tests/service/video_module/` 等
  - 每个包目录维护 `*_test.md` 说明文档
  - 多模块参与时放入主模块对应的 test 目录
  - E2E 统一放入 `tests/e2e/`
- 将现有 `_smoke_test.py` 重写为 **pytest 格式的 repository 冒烟测试**，覆盖组 A + 组 B 共 13 个 Repo
- 补充 **异常路径测试**：FK 约束、unique 冲突、不存在的记录操作、空值
- 构建 **基于 SQLite 的 CI 测试架构**：`tests/conftest.py` 提供 fixture（自动建表/回滚/清理）
- 新增一个 **repository 集成测试示例**（多 Repo 协作场景：创建 View → 关联设备 → 删除 View → 验证设备释放）
- 创建 `tests/e2e/` 骨架，预留端到端测试入口

## Capabilities

### New Capabilities

- `test-organization-standard`: 测试目录组织规范，作为项目强制约定写入 openspec
- `repo-smoke-tests`: 全部 13 个 Repository 的 pytest 冒烟测试（基础 CRUD + 特有方法 + 异常路径）
- `repo-integration-test`: 多 Repo 协作集成测试示例（View 生命周期 → 设备占用/释放）
- `sqlite-ci-fixtures`: SQLite 测试基础设施（conftest.py fixtures、自动建表、事务回滚）
- `e2e-skeleton`: E2E 测试骨架目录与说明文档

### Modified Capabilities

_无_（纯新增测试基础设施，不修改现有模块）

## Impact

- 新增 `tests/` 目录及子包结构
- 新增 `tests/conftest.py`（CI fixtures）
- 迁移 `_smoke_test.py` → `tests/repository/test_*.py`
- 新增 `pytest` 开发依赖（`pytest`, `pytest-cov`, `httpx`）
- 新增 `openspec/specs/test-organization-standard/spec.md`（规范文档）

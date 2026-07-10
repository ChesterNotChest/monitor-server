# Project Layout

**Purpose:** 定义项目文件层级约定——根目录仅 CD 配置，代码工作区为 `monitor-server/`。

## Requirements

### Requirement: 代码工作区为 `monitor-server/`

系统 SHALL 以 `monitor-server/` 为代码工作区。所有应用代码 SHALL 位于 `monitor-server/src/` 下。构建配置文件（Dockerfile、environment.yml、requirements.txt）SHALL 位于 `monitor-server/` 层级。运行时配置文件（.env、.env.example）SHALL 位于 `monitor-server/` 层级。

#### Scenario: 开发者定位代码

- **WHEN** 开发者打开项目
- **THEN** 所有 Python 模块在 `monitor-server/src/` 下，`cd monitor-server` 后所有命令生效

#### Scenario: Docker 构建

- **WHEN** `docker-compose.prod.yml` 使用 `context: ./monitor-server`
- **THEN** Dockerfile、requirements.txt、environment.yml 均在 `monitor-server/` 下可被 COPY 指令访问

### Requirement: 根目录仅放 CD 与项目级配置文件

仓库根目录 SHALL 仅包含以下文件类型：
- CI/CD 配置（Jenkinsfile、docker-compose.prod.yml）
- 项目元文件（README.md、pytest.ini、.gitignore）
- 子目录入口（monitor-server/、nginx/、srs/、openspec/）
- 版本控制（.git/、.claude/、.codex/）

根目录 SHALL NOT 放置 `.py` 测试文件、`.env` 文件、或构建配置文件。

#### Scenario: 根目录文件列表

- **WHEN** 查看仓库根目录
- **THEN** 仅出现 `Jenkinsfile`、`docker-compose.prod.yml`、`pytest.ini`、`README.md`、`.gitignore` 及 `monitor-server/`、`nginx/`、`srs/`、`openspec/` 子目录

### Requirement: 测试文件归入 `src/tests/`

所有 pytest 测试文件 SHALL 位于 `monitor-server/src/tests/` 下，按 `src/` 镜像结构组织子目录。根目录 SHALL NOT 包含测试文件。

#### Scenario: 运行全量测试

- **WHEN** 开发者在 `monitor-server/` 下执行 `pytest src/tests/`
- **THEN** 所有测试被收集，无漏网根目录文件

### Requirement: 构建配置与代码同层

Dockerfile、environment.yml、requirements.txt SHALL 位于 `monitor-server/` 层级——与 `src/` 并列，不与 `src/` 嵌套。

#### Scenario: 构建上下文一致

- **WHEN** CI 使用 `context: ./monitor-server` 构建镜像
- **THEN** Dockerfile、requirements.txt 在同一上下文内，COPY 路径不跨层级

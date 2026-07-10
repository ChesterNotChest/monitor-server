# No Claude Commits

**Purpose:** 禁止 AI 助手以任何身份向本仓库提交代码。所有 commit 必须由真实团队成员执行。

## Requirements

### Requirement: 禁止 AI 提交
系统 SHALL 拒绝任何作者（Author）或提交者（Committer）字段包含 `claude`、`anthropic`、`noreply`、`ai-assistant` 等非人类标识的 commit 进入主分支。

### Requirement: AI 仅修改工作区
AI 助手 SHALL 仅在工作区（working tree）中创建、编辑文件。`git add`、`git commit`、`git push` 操作 SHALL 由人类团队成员手动执行。

#### Scenario: AI 误执行 commit
- **WHEN** AI 助手执行了 `git commit`
- **THEN** 人类操作者 SHALL 在 push 前执行 `git reset --soft HEAD~1` 撤销，保留工作区改动

#### Scenario: 检查提交历史
- **WHEN** 审查 `git log --all --format="%an %ae"`
- **THEN** 所有条目的作者和邮箱均为团队成员真实身份

### Requirement: Co-Authored-By 豁免
如果人类成员在 commit message 中手动添加 `Co-Authored-By: Claude <noreply@anthropic.com>`，SHALL 视为该成员的有意识署名行为，而非 AI 自主提交，允许通过。

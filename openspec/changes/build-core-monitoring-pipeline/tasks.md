# Tasks — 全量监控能力

> 已拆分为两份独立文件，便于分工协作。

| 文件 | 负责人 | 范围 | 任务数 |
|------|--------|------|--------|
| [tasks-part-a.md](tasks-part-a.md) | ___ | 基础层：模型(5)、配置(5)、Schema(5)、Repository 扩展(3)、Network(5) | 23 |
| [tasks-part-b.md](tasks-part-b.md) | ___ | 功能层：清理(2)、Service(11)、API路由(3)、App集成(3)、Debug靶子(2)、测试(13) | 33 |

**协作方式**：Part B 可在 Part A 接口稳定后开始，或使用 mock repository + mock ConnectionRegistry 先行并行开发，Part A 完成后切换真实实现。接口契约见 `tasks-part-a.md` 末尾。

# 采用 Notion 数据源（Data Sources）模型

`notion-client` 3.x 配合 Notion 2025-09-03+ 的 API，把「查询行」和「创建页面」从 database 迁移到了 data source（`databases.query` 已不存在）。我们随之把 Notion 版本头固定为 `2026-03-11`，统一用 `data_source_id` 建页与查询，而不是降级到仍带 `databases.query` 的旧版 SDK。

**状态**：accepted

## Considered Options

- **降级 `notion-client` 到 2.x + 版本头 `2022-06-28`**（保留 `databases.query`）：改动最小，但把项目钉在 Notion 正在淘汰的旧模型上，属于技术债，故不采用。

## Consequences

- 需要先从 `database_id` 解析出 `data_source_id`（我们的库是单数据源）；已加 `config.get_data_source_id()`。
- 建页 parent 用 `{"type": "data_source_id", "data_source_id": ...}`；查询用 `notion.data_sources.query(data_source_id=...)`。
- 这也是后续「去重」（查询已存在的 Job Posting）的基础。

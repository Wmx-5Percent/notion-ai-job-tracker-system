# 单一数据库统一「发现」与「申请」

我们把自动发现的 Job Posting 和我已在投的 Application 放在**同一个 Notion 数据库**里，用 `Application Status` 生命周期区分阶段，并用 Notion View 隔离「待筛选的噪音」和「在投的申请」。选它是因为单一真相源让去重最简单、无需跨库同步；代价是申请视图不再天然干净，要靠 View 过滤。

**状态**：accepted

## Considered Options

- **两个库**（`Job Pool` 原始发现 → 晋升到 `Applications`）：申请表绝对干净，但要额外维护「晋升」逻辑和两边去重，复杂度与出错面更大，故不采用。

## Consequences

- 抓取程序只能写「发现阶段」的状态（如 `New`），**绝不能覆盖人工设置的申请状态**（如 `Applied` / `Interview`）。
- 需要给现有 `Application Status` 增加发现阶段选项（`New` / `Shortlist` / `Skip` 等，具体在下一步决定）。

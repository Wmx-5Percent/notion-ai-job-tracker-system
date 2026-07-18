# Job Posting 的唯一键 = (Source, External Job ID)

我们用 `(Source, External Job ID)` 作为 Job Posting 的去重唯一键（`Source` 如 greenhouse/lever/ashby，`External Job ID` 是 ATS 给的稳定职位号）。每次抓取先把 Notion 里已有的键拉成内存集合，命中就跳过、否则新建 `New`，天然幂等。

**状态**：accepted

## Considered Options

- **`Job URL` 作主键**：URL 可能带 tracking 参数或发生变化，不稳定，故只存不作键。
- **`title + company`**：同公司同名岗位在多城市各发一条时会被误判为同一个，不采用。

## Consequences

- 岗位下架后以**新** job id 重新发布 → 视为新的 Job Posting（会重新出现在 `New`，值得重新关注）。这是刻意选择。
- schema 需要 `Source` 与 `External Job ID` 两个字段（在字段清单里落实）。

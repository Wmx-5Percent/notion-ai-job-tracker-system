# Notion Schema（Job Application Tracker）

本表同时承载 Job Posting（发现）与 Application（申请），用 `Application Status`
区分生命周期，用 View 分离「待筛选噪音」与「在投申请」（见 ADR-0001）。
查询与建页都走 data source（见 ADR-0002）。

## 字段

### 机器在「建行」时写（此后由人工接管）
| 属性 | 类型 | 说明 |
|---|---|---|
| `Job Title` | title | 职位名 |
| `Company` | rich_text | 公司 |
| `URL` | url | 原始职位链接 |
| `Source` | select | `greenhouse` / `lever` / `ashby` |
| `External Job ID` | rich_text | ATS 稳定职位号；与 `Source` 组成唯一键（ADR-0003） |
| `Location` | rich_text | 地点（用于过滤 US/Remote + 展示） |
| `Posted Date` | date | ATS 发布时间（新鲜度 / 早投信号） |
| `Track` | select | `AI/LLM` · `Data` · `MLE` · `SWE` · `Other`（标题关键词粗分） |
| `Application Status` | status | 建行写 `New`；**之后只由人工改** |
| （页面正文 body） | blocks | **完整 JD**（切段写入正文，绕开 rich_text 的 ~2000 字上限） |

### 纯人工（机器永不写）
`Company Type`(rich_text) · `Rejected Phase`(select) · `Application Date`(date) · `Reminders`(rich_text)

### 内置
`Created time`（Notion 自带）＝「系统首次发现时间」，无需自建字段。

## Status 选项（最终）
`New`（机器入口 / 新鲜） · `Shortlist` · `Skip` · `Applied` · `Moved Forward` · `Interview` · `Accepted` · `Rejected` · `Closed`

铁律：机器只在建行时写 `New`；行一旦存在，**绝不改** Status。

## 推迟到后续阶段（现在不加）
`Match Score` · `Priority` · `Skills` · `Last Seen` · `JD Hash` · `Internship` 标志 等（LLM / 幂等阶段再议）。

## Notion 迁移清单（先在 sandbox 做，测好再对 prod 做一遍）
1. **`Application Status` 加选项**：`New`、`Shortlist`、`Skip`、`Closed`；删除 `Not started`（prod 有 0 行使用，安全）。
2. **新增属性**：`Source`(select) · `External Job ID`(text) · `Location`(text) · `Posted Date`(date) · `Track`(select：`AI/LLM`/`Data`/`MLE`/`SWE`/`Other`)。
3. **删除属性**：`Job Description`（完整 JD 已在正文）。

> ⚠️ 约束：Notion API **无法创建 `status` 选项**，所以第 1 步必须在 **Notion UI** 手动做，否则 collector 写 `Application Status = New` 会报错。`select` 选项（`Source`/`Track`）和新属性可以手动加，也可以之后用脚本加。

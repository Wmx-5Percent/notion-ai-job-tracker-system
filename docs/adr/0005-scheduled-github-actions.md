# 定时抓取：GitHub Actions 每日两次 cron

我们用 GitHub Actions 定时（每天两次，13:00 + 01:00 UTC）在云端跑 `main.py`，自动轮询各 ATS 并把新职位写入 Notion，取代"人手在本地记得跑"。这样 Summer-2027 实习在 8–11 月陆续开放时能被**自动**捕获、当天入库，无需盯着。

**状态**：accepted

## Decision

- **触发**：`schedule` 两个 cron（`0 13 * * *` 与 `0 1 * * *`，UTC）+ `workflow_dispatch` 手动触发（输入 `target` 可选 `sandbox`/`prod`）。
- **目标库**：定时任务**先写 SANDBOX**（`python main.py`，默认即 sandbox）。PROD 尚未迁移完（Notion UI 需先加 `New/Shortlist/Skip/Closed` status 选项 + `Source/External Job ID/Location/Posted Date/Track` 属性、连接 "Job Tracker Bot"，见 `docs/notion-schema.md`）；迁移后把定时任务改成 `--prod`。
- **秘钥**：`NOTION_TOKEN` / `NOTION_SANDBOX_DATABASE_ID` /（将来）`NOTION_DATABASE_ID` 存为 GitHub **repo secrets**，绝不进代码或日志。工作流从 secrets 注入为环境变量，`jobtracker/config.py` 直接读 `os.environ`。
- **运行环境**：`ubuntu-latest` + Python 3.12；`pip install -r requirements.txt`。`notion-client` 锁 `>=3.1,<4`，因为 data sources API 只在 3.x（ADR-0002）。
- **日志**：非 TTY 下 `main.py` 的 reporter 自动安静（不刷新状态行），只留 kept 行 + 汇总，CI 日志干净。

## Considered Options

- **本地手动跑**：能用，但依赖人记得、易漏、开放高峰期覆盖不稳；不符合"自动捕获"目标。
- **付费聚合器 / 自建云函数 / cron 服务器**：额外成本与运维；GitHub Actions 免费额度足够每天两跑，且与代码同仓、易审计。

## Consequences

- Actions 定时任务**只在默认分支**上生效——仓库必须留在 GitHub（建议 **private**），且工作流要在默认分支。
- 每天两跑基本能在开放当天入库；覆盖率仍取决于 `config/companies.yaml` 清单（ADR-0004）。
- **切 PROD 前必须先按 `docs/notion-schema.md` 迁移**，否则写 `status=New` 会报错。切换只需把工作流里的运行命令改成 `--prod`（或用手动触发选 `prod`）。
- 秘钥轮换：Notion internal integration token 不过期，但更换 bot / DB 时需同步更新 repo secrets。
- 长期无提交时 GitHub 会自动停用定时任务（约 60 天），需偶尔 re-enable。

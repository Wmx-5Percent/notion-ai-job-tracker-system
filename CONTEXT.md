# Job Tracker 领域语言

本项目是一个「AI 原生的求职发现与追踪系统」：自动从外部数据源发现职位，结构化后写入 Notion，由我人工筛选、分批投递并追踪结果。本文件只收录本项目特有的领域术语，不含实现细节。

## Language

**Job Posting（职位发布）**:
系统从外部数据源发现并记录的一条招聘信息（公司 + 职位 + JD + 链接）。它是追踪表里的一行，也是系统的基本单位；一条 Job Posting 可能最终并不会被投递。
_Avoid_: Job, Listing, Opportunity, 岗位, 职位

**Application（申请）**:
同一条 Job Posting 进入「已投递及之后」的阶段。它不是单独的记录，而是该行生命周期的后半段（投递 → OA → 面试 → 结果）。
_Avoid_: Submission, 投递记录

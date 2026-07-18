# Job Tracker 领域语言

本项目是一个「AI 原生的求职发现与追踪系统」：自动从外部数据源发现职位，结构化后写入 Notion，由我人工筛选、分批投递并追踪结果。本文件只收录本项目特有的领域术语，不含实现细节。

## Language

**Job Posting（职位发布）**:
系统从外部数据源发现并记录的一条招聘信息（公司 + 职位 + JD + 链接）。它是追踪表里的一行，也是系统的基本单位；一条 Job Posting 可能最终并不会被投递。
_Avoid_: Job, Listing, Opportunity, 岗位, 职位

**Application（申请）**:
同一条 Job Posting 进入「已投递及之后」的阶段。它不是单独的记录，而是该行生命周期的后半段（投递 → OA → 面试 → 结果）。
_Avoid_: Submission, 投递记录

**Source（来源）**:
一条 Job Posting 来自哪个 ATS 数据源（如 `greenhouse` / `lever` / `ashby`）。
_Avoid_: Platform, Channel, Board

**Collector（采集器）**:
从一个 Source 发现 Job Posting 的适配器，实现统一的 `fetch_jobs()` 接口（见 `jobtracker/collectors/base.py`）。每个 Source（Greenhouse / Ashby / …，以后也可能是官网爬虫）是一个独立 Collector，在 registry 里加一行即可接入，互不影响。
_Avoid_: Scraper, Fetcher, Client

**Sink（写出口）**:
collect 流水线把一条新的 Job Posting 交给 Sink 落地：生产环境写入 Notion，测试用假 Sink 捕获。它是「写」这一侧的 seam。
_Avoid_: Writer, Repository

**External Job ID（外部职位号）**:
ATS 为一个职位分配的稳定标识。它与 `Source` 组成 Job Posting 的唯一键，用于去重。
_Avoid_: Job ID, Posting ID

**Track（方向）**:
一条 Job Posting 的岗位方向分类：`AI/LLM` · `Data` · `MLE` · `SWE` · `Other`。v1 由标题关键词粗分；`Other` 表示命中了实习/学生信号、但暂时分不出方向的在场岗位，留给人工 triage；后续可用 LLM 校正。
_Avoid_: Category, Role Type, 类别

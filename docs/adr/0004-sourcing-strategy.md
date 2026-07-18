# 岗位来源策略：per-company ATS 轮询 + 广清单 + 高召回过滤

我们靠轮询各公司的 ATS 公开 board（先 Greenhouse，后 Lever/Ashby）来发现职位，而**不用**付费聚合器或爬虫。覆盖面 = `config/companies.yaml` 里的公司数量，所以清单要当资产持续养大；过滤走**高召回**（标题沾边即收为 `New`，硬约束仅「实习 + 美国/Remote」），噪音由人工用 `Skip` 筛。

**状态**：accepted

## Considered Options

- **付费聚合器 / Google Jobs 类 API**：能跨公司搜，但花钱、数据不干净、有稳定性与 ToS 风险，不采用。
- **爬 LinkedIn**：ToS 风险 + 页面脆弱，不采用。

## Consequences

- 覆盖面受限于清单——漏掉不在清单里的公司是**已知代价**，靠持续扩清单 + 增加 Lever/Ashby collector 缓解。
- 高召回意味着 `New` 里天然有噪音，这是**刻意**的，配合 `New → Shortlist / Skip` 三态消化。
- 每次抓取都实测每个 board token，只保留能返回职位的（清单会自动去掉失效公司）。

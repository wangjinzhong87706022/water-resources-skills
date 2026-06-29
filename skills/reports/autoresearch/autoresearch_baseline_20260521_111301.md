# Autoresearch BASELINE 报告

> 时间: 2026-05-21 11:13:01
> 阶段: baseline

## gate-pump-operation

| 指标 | 值 |
|------|-----|
| **通过率** | 10/15 (66.7%) |
| **平均耗时** | 164.7s |

| 测试输入 | completes_fast | has_domain_kw | has_numbers | response_detailed | not_timeout | 耗时 |
|----------|------|------|------|------|------|------|
| 闸站列表 | ✅ | ✅ | ✅ | ✅ | ✅ | 156.03s |
| 单站详情 | ✅ | ✅ | ✅ | ✅ | ✅ | 38.0s |
| 泵站聚合（L2超时题） | ❌ | ❌ | ❌ | ❌ | ❌ | 300.1s |

**失败项:**
- [泵站聚合（L2超时题）] completes_fast: Response completes within 180 seconds?
- [泵站聚合（L2超时题）] has_domain_kw: Contains 2+ of: 闸/泵/开度/流量/启闭/上下游/堰?
- [泵站聚合（L2超时题）] has_numbers: Contains 3+ numeric values?
- [泵站聚合（L2超时题）] response_detailed: Response is longer than 200 characters?
- [泵站聚合（L2超时题）] not_timeout: Response does not contain TIMEOUT or ERROR markers?

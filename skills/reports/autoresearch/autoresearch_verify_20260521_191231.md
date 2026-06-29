# Autoresearch VERIFY 报告

> 时间: 2026-05-21 19:12:31
> 阶段: verify

## gate-pump-operation

| 指标 | 值 |
|------|-----|
| **通过率** | 13/20 (65.0%) |
| **平均耗时** | 207.4s |

| 测试输入 | completes_fast | has_domain_kw | has_numbers | response_detailed | not_timeout | 耗时 |
|----------|------|------|------|------|------|------|
| 闸站列表 | ❌ | ✅ | ✅ | ✅ | ✅ | 183.58s |
| 单站详情 | ✅ | ✅ | ✅ | ✅ | ✅ | 82.76s |
| 泵站聚合（L2超时题） | ❌ | ✅ | ✅ | ✅ | ✅ | 263.03s |
| 堰闸排名（L3超时题） | ❌ | ❌ | ❌ | ❌ | ❌ | 300.12s |

**失败项:**
- [闸站列表] completes_fast: Response completes within 180 seconds?
- [泵站聚合（L2超时题）] completes_fast: Response completes within 180 seconds?
- [堰闸排名（L3超时题）] completes_fast: Response completes within 180 seconds?
- [堰闸排名（L3超时题）] has_domain_kw: Contains 2+ of: 闸/泵/开度/流量/启闭/上下游/堰?
- [堰闸排名（L3超时题）] has_numbers: Contains 3+ numeric values?
- [堰闸排名（L3超时题）] response_detailed: Response is longer than 200 characters?
- [堰闸排名（L3超时题）] not_timeout: Response does not contain TIMEOUT or ERROR markers?

# Autoresearch VERIFY 报告

> 时间: 2026-05-21 11:34:43
> 阶段: verify

## rainfall

| 指标 | 值 |
|------|-----|
| **通过率** | 10/12 (83.3%) |
| **平均耗时** | 145.1s |

| 测试输入 | completes_fast | has_domain_kw | has_numbers | response_detailed | 耗时 |
|----------|------|------|------|------|------|
| 单站实时查询 | ✅ | ✅ | ✅ | ❌ | 84.73s |
| 年度聚合+极值 | ❌ | ✅ | ✅ | ✅ | 254.17s |
| 多站累计 | ✅ | ✅ | ✅ | ✅ | 96.4s |

**失败项:**
- [单站实时查询] response_detailed: Response is longer than 200 characters?
- [年度聚合+极值] completes_fast: Response completes within 180 seconds?

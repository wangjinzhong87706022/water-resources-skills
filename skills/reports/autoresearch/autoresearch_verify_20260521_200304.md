# Autoresearch VERIFY 报告

> 时间: 2026-05-21 20:03:04
> 阶段: verify

## gate-pump-operation

| 指标 | 值 |
|------|-----|
| **通过率** | 18/20 (90.0%) |
| **平均耗时** | 177.3s |

| 测试输入 | completes_fast | has_domain_kw | has_numbers | response_detailed | not_timeout | 耗时 |
|----------|------|------|------|------|------|------|
| 闸站列表 | ✅ | ✅ | ✅ | ✅ | ✅ | 136.94s |
| 单站详情 | ✅ | ✅ | ✅ | ✅ | ✅ | 99.21s |
| 泵站聚合（L2超时题） | ❌ | ✅ | ✅ | ✅ | ✅ | 292.32s |
| 堰闸排名（L3超时题） | ❌ | ✅ | ✅ | ✅ | ✅ | 180.86s |

**失败项:**
- [泵站聚合（L2超时题）] completes_fast: Response completes within 180 seconds?
- [堰闸排名（L3超时题）] completes_fast: Response completes within 180 seconds?

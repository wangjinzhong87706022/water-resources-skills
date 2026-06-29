# Autoresearch VERIFY 报告

> 时间: 2026-05-21 20:17:46
> 阶段: verify

## gate-pump-operation

| 指标 | 值 |
|------|-----|
| **通过率** | 19/20 (95.0%) |
| **平均耗时** | 139.7s |

| 测试输入 | completes_fast | has_domain_kw | has_numbers | response_detailed | not_timeout | 耗时 |
|----------|------|------|------|------|------|------|
| 闸站列表 | ✅ | ✅ | ✅ | ✅ | ✅ | 91.16s |
| 单站详情 | ✅ | ✅ | ✅ | ✅ | ✅ | 108.35s |
| 泵站聚合（L2超时题） | ❌ | ✅ | ✅ | ✅ | ✅ | 183.9s |
| 堰闸排名（L3超时题） | ✅ | ✅ | ✅ | ✅ | ✅ | 175.53s |

**失败项:**
- [泵站聚合（L2超时题）] completes_fast: Response completes within 180 seconds?

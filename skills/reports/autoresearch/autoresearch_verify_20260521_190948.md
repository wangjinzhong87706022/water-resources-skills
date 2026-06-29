# Autoresearch VERIFY 报告

> 时间: 2026-05-21 19:09:48
> 阶段: verify

## water-warning

| 指标 | 值 |
|------|-----|
| **通过率** | 12/20 (60.0%) |
| **平均耗时** | 165.3s |

| 测试输入 | completes_fast | has_domain_kw | has_numbers | response_detailed | not_timeout | 耗时 |
|----------|------|------|------|------|------|------|
| 超警查询 | ❌ | ❌ | ✅ | ✅ | ✅ | 211.71s |
| 多站预警汇总 | ✅ | ❌ | ✅ | ✅ | ✅ | 70.28s |
| 跨库水质预警 | ❌ | ❌ | ❌ | ❌ | ❌ | 300.12s |
| 多河道汇总（L3超时题） | ✅ | ✅ | ✅ | ✅ | ✅ | 78.91s |

**失败项:**
- [超警查询] completes_fast: Response completes within 180 seconds?
- [超警查询] has_domain_kw: Contains 2+ of: 预警/超警戒/超保证/防洪/水质?
- [多站预警汇总] has_domain_kw: Contains 2+ of: 预警/超警戒/超保证/防洪/水质?
- [跨库水质预警] completes_fast: Response completes within 180 seconds?
- [跨库水质预警] has_domain_kw: Contains 2+ of: 预警/超警戒/超保证/防洪/水质?
- [跨库水质预警] has_numbers: Contains 3+ numeric values?
- [跨库水质预警] response_detailed: Response is longer than 200 characters?
- [跨库水质预警] not_timeout: Response does not contain TIMEOUT or ERROR markers?

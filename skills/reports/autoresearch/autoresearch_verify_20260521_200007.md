# Autoresearch VERIFY 报告

> 时间: 2026-05-21 20:00:07
> 阶段: verify

## water-forecast

| 指标 | 值 |
|------|-----|
| **通过率** | 15/16 (93.8%) |
| **平均耗时** | 131.2s |

| 测试输入 | completes_fast | has_domain_kw | has_numbers | response_detailed | 耗时 |
|----------|------|------|------|------|------|
| 任务状态查询 | ✅ | ✅ | ✅ | ✅ | 107.47s |
| 单站预测 | ✅ | ✅ | ✅ | ✅ | 132.14s |
| 多站聚合 | ✅ | ✅ | ✅ | ✅ | 76.5s |
| 预测vs实际对比（L3超时题） | ❌ | ✅ | ✅ | ✅ | 208.64s |

**失败项:**
- [预测vs实际对比（L3超时题）] completes_fast: Response completes within 180 seconds?

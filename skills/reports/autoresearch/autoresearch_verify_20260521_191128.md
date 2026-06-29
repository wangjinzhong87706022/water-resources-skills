# Autoresearch VERIFY 报告

> 时间: 2026-05-21 19:11:28
> 阶段: verify

## water-forecast

| 指标 | 值 |
|------|-----|
| **通过率** | 11/16 (68.8%) |
| **平均耗时** | 192.9s |

| 测试输入 | completes_fast | has_domain_kw | has_numbers | response_detailed | 耗时 |
|----------|------|------|------|------|------|
| 任务状态查询 | ✅ | ✅ | ✅ | ✅ | 105.52s |
| 单站预测 | ❌ | ✅ | ✅ | ✅ | 214.71s |
| 多站聚合 | ✅ | ✅ | ✅ | ✅ | 151.45s |
| 预测vs实际对比（L3超时题） | ❌ | ❌ | ❌ | ❌ | 300.11s |

**失败项:**
- [单站预测] completes_fast: Response completes within 180 seconds?
- [预测vs实际对比（L3超时题）] completes_fast: Response completes within 180 seconds?
- [预测vs实际对比（L3超时题）] has_domain_kw: Contains 2+ of: 预测/预报/任务/模型/断面/水位?
- [预测vs实际对比（L3超时题）] has_numbers: Contains 3+ numeric values?
- [预测vs实际对比（L3超时题）] response_detailed: Response is longer than 200 characters?

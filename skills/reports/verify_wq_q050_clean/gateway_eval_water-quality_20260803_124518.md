# DeerFlow Gateway 真实平台评测报告

> 模式: **Gateway /api/runs/wait（真实 agent 全栈）**
> Gateway: http://localhost:8001 | 模型: 平台默认

- 时间: 20260803_124518
- 用例: 6 | 平均分: 0.658 | 通过率: 66.7%

| Q# | Skill | Level | Score | SQLs | Rounds | 耗时 | 状态 |
|---|---|---|---|---|---|---|---|
| Q050 | water-quality | L3 | 0.000 | 0 | 0 | 600s | ✗ |
| Q051 | water-quality | L3 | 0.300 | 0 | 1 | 14s | ✓ |
| Q052 | water-quality | L3 | 1.000 | 1 | 5 | 235s | ✓ |
| Q053 | water-quality | L3 | 0.950 | 5 | 10 | 401s | ✓ |
| Q054 | water-quality | L3 | 0.750 | 3 | 4 | 286s | ✓ |
| Q055 | water-quality | L3 | 0.950 | 4 | 14 | 459s | ✓ |

## 低分 Case（< 0.6）

### Q050 [water-quality/L3] — 0.000

**Q**: 瘦西湖水质监测的具体指标有哪些？最近一个月哪些指标变化最显著？

**最终答案**（前 400 字）:
```

```

**错误**: timed out

**评分明细**: {"has_valid_response": 0.0, "sql_generated": 0.0, "sql_replay_ok": 0.0, "result_quality": 0.0, "trace_sanity": 0.0}

---

### Q051 [water-quality/L3] — 0.300

**Q**: 查询一段时间内所有水质站的水质变化趋势。

**最终答案**（前 400 字）:
```
我来帮您查询水质变化趋势。首先，我需要了解一些关键信息。


```

**评分明细**: {"has_valid_response": 1.0, "sql_generated": 0.0, "sql_replay_ok": 0.0, "result_quality": 0.0, "trace_sanity": 1.0}

---


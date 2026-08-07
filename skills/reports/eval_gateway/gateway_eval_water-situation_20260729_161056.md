# DeerFlow Gateway 真实平台评测报告

> 模式: **Gateway /api/runs/wait（真实 agent 全栈）**
> Gateway: http://localhost:8001 | 模型: 平台默认

- 时间: 20260729_161056
- 用例: 25 | 平均分: 0.781 | 通过率: 76.0%

| Q# | Skill | Level | Score | SQLs | Rounds | 耗时 | 状态 |
|---|---|---|---|---|---|---|---|
| Q001 | water-situation | L1 | 0.790 | 1 | 3 | 43s | ✓ |
| Q002 | water-situation | L1 | 1.000 | 1 | 4 | 59s | ✓ |
| Q003 | water-situation | L1 | 1.000 | 1 | 3 | 9s | ✓ |
| Q004 | water-situation | L1 | 0.740 | 6 | 10 | 112s | ✓ |
| Q005 | water-situation | L2 | 0.790 | 1 | 3 | 12s | ✓ |
| Q006 | water-situation | L2 | 1.000 | 2 | 3 | 13s | ✓ |
| Q007 | water-situation | L2 | 0.700 | 2 | 4 | 18s | ✓ |
| Q008 | water-situation | L2 | 1.000 | 4 | 7 | 115s | ✓ |
| Q009 | water-situation | L2 | 0.974 | 4 | 8 | 129s | ✓ |
| Q010 | water-situation | L2 | 0.809 | 1 | 4 | 122s | ✓ |
| Q011 | water-situation | L3 | 0.850 | 3 | 6 | 75s | ✓ |
| Q012 | water-situation | L3 | 0.450 | 3 | 11 | 292s | ✓ |
| Q013 | water-situation | L3 | 0.450 | 2 | 11 | 264s | ✓ |
| Q014 | water-situation | L3 | 0.450 | 4 | 11 | 286s | ✓ |
| Q015 | water-situation | L3 | 1.000 | 4 | 7 | 42s | ✓ |
| Q016 | water-situation | L3 | 1.000 | 1 | 3 | 15s | ✓ |
| Q017 | water-situation | L3 | 1.000 | 2 | 4 | 27s | ✓ |
| Q018 | water-situation | L3 | 0.850 | 5 | 7 | 160s | ✓ |
| Q019 | water-situation | L3 | 0.790 | 2 | 5 | 69s | ✓ |
| Q020 | water-situation | L3 | 0.500 | 4 | 7 | 83s | ✓ |
| Q021 | water-situation | L3 | 0.850 | 1 | 4 | 39s | ✓ |
| Q022 | water-situation | L3 | 0.740 | 7 | 10 | 101s | ✓ |
| Q023 | water-situation | L3 | 0.450 | 8 | 11 | 100s | ✓ |
| Q024 | water-situation | L3 | 0.500 | 4 | 5 | 44s | ✓ |
| Q025 | water-situation | L3 | 0.850 | 3 | 5 | 49s | ✓ |

## 低分 Case（< 0.6）

### Q012 [water-situation/L3] — 0.450

**Q**: 古运河2024年2、3月份水位对比。

**平台 SQL**:
```sql
SELECT 
    DATE(r.tm) AS `date`,
    ROUND(AVG(r.z), 3) AS avg_level
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
  AND r.tm >= '2024-02-01' AND r.tm < '2024-04-01'
  AND r.z IS NOT NULL
GROUP BY DATE(r.tm)
ORDER BY `date`
```

**最终答案**（前 400 字）:
```

```

**评分明细**: {"has_valid_response": 0.0, "sql_generated": 1.0, "sql_replay_ok": 1.0, "result_quality": 0.0, "trace_sanity": 0.5}

---

### Q013 [water-situation/L3] — 0.450

**Q**: 请比较2023年和2024年古运河的平均水位。

**平台 SQL**:
```sql
SELECT 
    r.stcd,
    b.stnm,
    YEAR(r.tm) AS year,
    COUNT(r.z) AS data_count,
    ROUND(AVG(r.z), 3) AS avg_level,
    ROUND(MAX(r.z), 3) AS max_level,
    ROUND(MIN(r.z), 3) AS min_level
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
  AND r.tm >= '2023-01-01' AND r.tm < '2025-01-01'
  AND r.z IS NOT NULL
GROUP BY r.stcd, b.stnm, YEAR(r.tm)
ORDER BY year, r.stcd
```

**最终答案**（前 400 字）:
```

```

**评分明细**: {"has_valid_response": 0.0, "sql_generated": 1.0, "sql_replay_ok": 1.0, "result_quality": 0.0, "trace_sanity": 0.5}

---

### Q014 [water-situation/L3] — 0.450

**Q**: 古运河2024年2月水位分布情况。

**平台 SQL**:
```sql
SELECT DATE(r.tm) as dt, b.stcd, b.stnm, ROUND(AVG(r.z), 2) as daily_avg_z
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
  AND r.tm >= '2024-02-01' AND r.tm < '2024-03-01'
  AND r.z IS NOT NULL
GROUP BY DATE(r.tm), b.stcd, b.stnm
ORDER BY b.lttd DESC, dt
```

**最终答案**（前 400 字）:
```

```

**评分明细**: {"has_valid_response": 0.0, "sql_generated": 1.0, "sql_replay_ok": 1.0, "result_quality": 0.0, "trace_sanity": 0.5}

---

### Q023 [water-situation/L3] — 0.450

**Q**: 查询水位站宝应本月内水位数据变化趋势。

**平台 SQL**:
```sql
SELECT r.tm, ROUND(r.z, 3) as z
FROM st_river_r r
WHERE r.stcd = '51005000'
  AND r.tm >= '2026-05-01' AND r.tm < '2026-06-01'
ORDER BY r.tm
```

**最终答案**（前 400 字）:
```

```

**评分明细**: {"has_valid_response": 0.0, "sql_generated": 1.0, "sql_replay_ok": 1.0, "result_quality": 0.0, "trace_sanity": 0.5}

---

### Q020 [water-situation/L3] — 0.500

**Q**: 扬州水利枢纽3月份平均水位。

**平台 SQL**:
```sql
SELECT stcd, COUNT(*) as cnt, MIN(tm) as min_tm, MAX(tm) as max_tm FROM st_pump_r WHERE stcd IN ('HP0071002004000012', 'HP0101002004000063') GROUP BY stcd
```

**最终答案**（前 400 字）:
```

```

**评分明细**: {"has_valid_response": 0.0, "sql_generated": 1.0, "sql_replay_ok": 1.0, "result_quality": 0.0, "trace_sanity": 1.0}

---

### Q024 [water-situation/L3] — 0.500

**Q**: 古运河8月的水位数据与扬州闸6月的水位数据对比，各自的平均水位、最高水位和最低水位分别是多少？

**平台 SQL**:
```sql
SELECT r.stcd, b.stnm, MIN(r.tm) as min_tm, MAX(r.tm) as max_tm, COUNT(*) as cnt FROM st_river_r r JOIN st_stbprp_b b ON r.stcd = b.stcd WHERE b.stnm LIKE '%扬州闸%' GROUP BY r.stcd, b.stnm ORDER BY r.stcd
```

**最终答案**（前 400 字）:
```

```

**评分明细**: {"has_valid_response": 0.0, "sql_generated": 1.0, "sql_replay_ok": 1.0, "result_quality": 0.0, "trace_sanity": 1.0}

---


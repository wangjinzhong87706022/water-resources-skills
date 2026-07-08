<!-- SOURCE: adapted from knowledge-work-plugins/data/skills/sql-queries/SKILL.md
     UPSTREAM_LINES: 428 | ADAPTED_LINES: ~330 | MIGRATION: COMPLETE | DATE: 2026-07-08
     注：通用版为多方言仓库 SQL；本版已收敛为水利 MySQL 单库，并按 5.7/8.0 双写法重写。 -->
# SQL 通用查询模式

> 超越基础 SELECT-FROM-WHERE 的常用分析模式。与 `sql_safety_rules.md`（安全规则）、`sql_quality_check.md`（质量审查）配合使用。

> **⚠️ 当前基线 = MySQL 5.7.32**，**不支持窗口函数（`ROW_NUMBER`/`LAG`/`OVER`）、CTE（`WITH`）、`LATERAL`、`FULL JOIN`**。
> 下文每个需要这些特性的模式都给两套写法：**① 当前基线（5.7 可跑）** + **② 现代写法（8.0+ / 升级迁移后）**。
> 方言差异详见 `sql_dialects/`（族划分、5.7↔8.0 检查清单、国产库迁移）。

---

## 窗口函数（去重 / 排名 / 差分 / 移动平均 / 首末值）

> 窗口函数是 MySQL **8.0+** 特性。5.7 用相关子查询、自连接、或"SQL 取数 + pandas"替代。

### 排序/排名：各站水位高低

```sql
-- ① 当前基线（5.7）：相关子查询计数法（站多时 O(n²)，务必 LIMIT 收窄）
SELECT a.stcd, a.z,
       (SELECT COUNT(*) + 1 FROM st_river_r b
        WHERE b.z > a.z AND b.tm >= DATE_SUB(NOW(), INTERVAL 1 DAY)) AS z_rank
FROM st_river_r a
WHERE a.tm >= DATE_SUB(NOW(), INTERVAL 1 DAY)
ORDER BY z_rank LIMIT 20;
```
```sql
-- ② 现代写法（8.0+）
SELECT stcd, z, ROW_NUMBER() OVER (ORDER BY z DESC) AS z_rank
FROM st_river_r
WHERE tm >= DATE_SUB(NOW(), INTERVAL 1 DAY);
```

### 差分：逐条水位变化（替代 LAG）

```sql
-- ① 当前基线（5.7）：自连接找"上一条"
SELECT cur.stcd, cur.tm, cur.z,
       ROUND(cur.z - prev.z, 2) AS z_change
FROM st_river_r cur
LEFT JOIN st_river_r prev
  ON prev.stcd = cur.stcd
 AND prev.tm = (SELECT MAX(tm) FROM st_river_r p
                WHERE p.stcd = cur.stcd AND p.tm < cur.tm)
WHERE cur.stcd = '50801450' AND cur.tm >= DATE_SUB(NOW(), INTERVAL 3 DAY)
ORDER BY cur.tm;
```
```sql
-- ② 现代写法（8.0+）
SELECT stcd, tm, z,
       COALESCE(ROUND(z - LAG(z) OVER (PARTITION BY stcd ORDER BY tm), 2), 0) AS z_change
FROM st_river_r
WHERE stcd = '50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 3 DAY);
```

### 移动平均 / 累计求和（5.7 无窗口 → SQL 取数 + pandas）

> 5.7 用用户变量 `@rn`/`@s` 模拟窗口函数**排序不可靠**（优化器可能重排求值），**不建议**。务实做法见下。

```python
import pandas as pd
from db import query
rows = query("""SELECT DATE(tm) AS dt, AVG(z) AS z_avg
                FROM st_river_r
                WHERE stcd='50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(tm) ORDER BY dt""")
df = pd.DataFrame(rows)
df['ma_7d'] = df['z_avg'].astype(float).rolling(7, min_periods=1).mean()   # 7 日移动平均
```
```sql
-- ② 现代写法（8.0+，纯 SQL）
SELECT stcd, tm, z,
       AVG(z) OVER (PARTITION BY stcd ORDER BY tm ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS z_ma_7d
FROM st_river_r WHERE stcd='50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```

### 每日最高/最低（替代 FIRST_VALUE）

```sql
-- ① 当前基线（5.7）：GROUP BY 直接聚合（取"发生时间"需再自连接）
SELECT DATE(tm) AS dt, MAX(z) AS z_max, MIN(z) AS z_min
FROM st_river_r
WHERE stcd='50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(tm) ORDER BY dt;
```

### 去重：保留每站最新记录

```sql
-- ① 当前基线（5.7）：相关子查询
SELECT r.stcd, r.tm, r.z
FROM st_river_r r
WHERE r.tm = (SELECT MAX(r2.tm) FROM st_river_r r2
              WHERE r2.stcd = r.stcd AND r2.tm >= DATE_SUB(NOW(), INTERVAL 7 DAY))
  AND r.tm >= DATE_SUB(NOW(), INTERVAL 7 DAY);
```
```sql
-- ② 现代写法（8.0+）
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY stcd ORDER BY tm DESC) AS rn
    FROM st_river_r WHERE tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)
) t WHERE rn = 1;
```

---

## CTE 分步构建（8.0+ 特性）

> `WITH … AS` 是 MySQL **8.0+** 特性，用于把复杂查询拆成可读的多步。**5.7 把每个 CTE 内联为嵌套子查询即可，逻辑等价**（见下方 ①）。

需求：扬州水文站 → 取最新水位 → 关联警戒水位 → 判断预警等级。

```sql
-- ① 当前基线（5.7）：内联子查询（CTE 逻辑等价展开）
SELECT stcd, stnm, z, tm, wrz, grz,
       CASE WHEN z > COALESCE(grz, 999) THEN '超保证'
            WHEN z > COALESCE(wrz, 999) THEN '超警戒'
            ELSE '正常' END AS warn_level
FROM (
   SELECT r.stcd, b.stnm, r.z, r.tm, f.wrz, f.grz
   FROM st_river_r r
   JOIN st_stbprp_b b  ON r.stcd = b.stcd
   LEFT JOIN st_rvfcch_b f ON UPPER(r.stcd) = f.STCD
   WHERE b.sttp IN ('ZZ','ZQ') AND b.stnm LIKE '%扬州%'
     AND r.tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)
) latest;
```
```sql
-- ② 现代写法（8.0+，CTE 更易读）
WITH target AS (SELECT stcd, stnm FROM st_stbprp_b
                WHERE sttp IN ('ZZ','ZQ') AND stnm LIKE '%扬州%'),
     latest AS (SELECT r.stcd, t.stnm, r.z, r.tm
                FROM st_river_r r JOIN target t ON r.stcd=t.stcd
                WHERE r.tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)),
     with_wrz AS (SELECT l.*, f.wrz, f.grz FROM latest l
                  LEFT JOIN st_rvfcch_b f ON UPPER(l.stcd)=f.STCD)
SELECT *, CASE WHEN z>COALESCE(grz,999) THEN '超保证'
               WHEN z>COALESCE(wrz,999) THEN '超警戒' ELSE '正常' END AS warn_level
FROM with_wrz;
```

---

## 留存/延续分析（数据完整性）

> 同一测站连续两日是否有数据。CTE 为 8.0+；5.7 把 `daily_activity` 内联为子查询。

```sql
-- ① 当前基线（5.7）
SELECT a.stcd, a.dt,
       CASE WHEN b.dt IS NOT NULL THEN 1 ELSE 0 END AS has_next_day
FROM (
   SELECT DISTINCT stcd, DATE(tm) AS dt FROM st_river_r
   WHERE tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
) a
LEFT JOIN (
   SELECT DISTINCT stcd, DATE(tm) AS dt FROM st_river_r
   WHERE tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
) b ON a.stcd = b.stcd AND b.dt = DATE_ADD(a.dt, INTERVAL 1 DAY);
```

---

## 漏斗分析（5.7 可跑，纯 CASE+聚合）

```sql
-- 水质从监测到超标警告的链路（各环节数据完备率）
SELECT
    COUNT(DISTINCT stcd) AS total_monitored,
    SUM(CASE WHEN dox    IS NOT NULL THEN 1 ELSE 0 END) AS has_do,
    SUM(CASE WHEN codmn  IS NOT NULL THEN 1 ELSE 0 END) AS has_codmn,
    SUM(CASE WHEN dox < 3 OR codmn > 10 THEN 1 ELSE 0 END) AS has_violation
FROM sl325.wq_pcp_d                                -- ⚠️ 水质表在 sl325 库；同服务器跨库查询，库名前缀即可
WHERE spt >= DATE_SUB(CURDATE(), INTERVAL 7 DAY);
```

---

## 跨表对比（双系列：实测 vs 预测）

> ⚠️ **MySQL（任何版本）不支持 `FULL JOIN`**。用 `LEFT JOIN ... UNION ... RIGHT JOIN` 模拟。

```sql
-- ① 当前基线（5.7）：UNION 模拟 FULL JOIN
SELECT COALESCE(a.hour_slot, f.hour_slot) AS tm, a.actual_z, f.forecast_z,
       ROUND(a.actual_z - f.forecast_z, 2) AS deviation
FROM (
   SELECT DATE_FORMAT(tm,'%Y-%m-%d %H:00:00') AS hour_slot, AVG(z) AS actual_z
   FROM st_river_r WHERE stcd='50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 2 DAY)
   GROUP BY DATE_FORMAT(tm,'%Y-%m-%d %H:00:00')
) a
LEFT JOIN (SELECT tm AS hour_slot, vals AS forecast_z FROM slztk.st_mx_preset_cal_r
           WHERE stcd='50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 2 DAY)) f
  ON a.hour_slot = f.hour_slot
UNION
SELECT COALESCE(a.hour_slot, f.hour_slot) AS tm, a.actual_z, f.forecast_z,
       ROUND(a.actual_z - f.forecast_z, 2) AS deviation
FROM (
   SELECT DATE_FORMAT(tm,'%Y-%m-%d %H:00:00') AS hour_slot, AVG(z) AS actual_z
   FROM st_river_r WHERE stcd='50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 2 DAY)
   GROUP BY DATE_FORMAT(tm,'%Y-%m-%d %H:00:00')
) a
RIGHT JOIN (SELECT tm AS hour_slot, vals AS forecast_z FROM slztk.st_mx_preset_cal_r
            WHERE stcd='50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 2 DAY)) f
  ON a.hour_slot = f.hour_slot;
```

---

## 分组 Top-N（每个河系水位最高的前 3 站）

```sql
-- ① 当前基线（5.7）：相关子查询计数法（按分区算排名）
SELECT r.stcd, b.stnm, b.sttp, r.z
FROM st_river_r r JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE r.tm >= DATE_SUB((SELECT MAX(tm) FROM st_river_r), INTERVAL 1 DAY)
  AND (SELECT COUNT(*) FROM st_river_r r2
       JOIN st_stbprp_b b2 ON r2.stcd=b2.stcd
       WHERE b2.sttp = b.sttp AND r2.z > r.z
         AND r2.tm >= DATE_SUB((SELECT MAX(tm) FROM st_river_r), INTERVAL 1 DAY)) < 3
ORDER BY b.sttp, r.z DESC;
```
```sql
-- ② 现代写法（8.0+）
SELECT stcd, stnm, sttp, z FROM (
   SELECT r.stcd, b.stnm, b.sttp, r.z,
          ROW_NUMBER() OVER (PARTITION BY b.sttp ORDER BY r.z DESC) AS rn
   FROM st_river_r r JOIN st_stbprp_b b ON r.stcd=b.stcd
   WHERE r.tm >= DATE_SUB((SELECT MAX(tm) FROM st_river_r), INTERVAL 1 DAY)
) t WHERE rn <= 3;
```

---

## 日期处理注意事项

| 场景 | 正确写法 | 错误写法 |
|------|---------|---------|
| 当前日期 | `CURDATE()` / `NOW()` | 硬编码 '2026-07-08' |
| 最近 N 天 | `tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)` | `DATEDIFF(...) <= 7`（低效） |
| 当月 | `tm >= DATE_FORMAT(CURDATE(), '%Y-%m-01')` | 手动算月初 |
| 昨天 | `tm >= CURDATE() - INTERVAL 1 DAY AND tm < CURDATE()` | `DATE(tm) = CURDATE() - 1` |
| 时间对齐 | 统一 UTC+8 | 混用不同时区时间戳 |
| 预测表时效 | 先 `SELECT MAX(tm)` 检查新鲜度 | 假设最新数据可用 |

> **分区表**（st_river_r, st_was_r, st_pump_r, st_pump_pa）的 WHERE 条件必须包含 `tm` 范围以触发分区裁剪，否则全分区扫描会超时。

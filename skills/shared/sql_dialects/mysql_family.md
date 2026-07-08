# MySQL 族方言指南（5.7 ↔ 8.0 ↔ TiDB / OceanBase）

> 适用：MySQL 5.7（**当前生产基线**）、MySQL 8.0+、TiDB、OceanBase(MySQL 模式)。
> 核心矛盾：**5.7 没有窗口函数 / CTE / LATERAL**，而 `sql_patterns.md` 的分析模式大量依赖它们。
> 本文件给出 5.7 下能跑的替代写法，以及升级到 8.0 的检查清单。

## 1. 5.7 能力边界（实测 MySQL 5.7.32）

| 特性 | 5.7 | 8.0+ | 影响 |
|------|:---:|:---:|------|
| 窗口函数 `ROW_NUMBER/LAG/LEAD/RANK/FIRST_VALUE … OVER` | ❌ | ✅ | 去重/排名/差分/移动平均/首末值 无法用纯 SQL |
| CTE `WITH … AS` | ❌ | ✅ | 多步查询只能内联成子查询或临时表 |
| 集合操作 `INTERSECT` / `EXCEPT` | ❌ | ✅(8.0.31) | 求交集/差集用 INNER JOIN / LEFT JOIN…IS NULL 子查询替代（见 2.6） |
| `LATERAL` 派生表 | ❌ | ✅(8.0.14) | 关联子查询在 FROM 子句无法表达 |
| `JSON_TABLE` | ❌ | ✅(8.0.14) | JSON 数组展开需应用层处理 |
| `JSON_EXTRACT` / `->` / `->>` | ✅ | ✅ | 可用 |
| 相关子查询 / 自连接 / 用户变量 `@x` | ✅ | ✅ | 5.7 的替代手段 |
| `GROUP BY` + 聚合 / `DATE_SUB` / `LIMIT` | ✅ | ✅ | 基础分析不受影响 |

## 2. 5.7 替代写法（每个对应 sql_patterns.md 的一个窗口函数模式）

### 2.1 去重：取每站最新水位（替代 `ROW_NUMBER() OVER(PARTITION BY … ORDER BY tm DESC)`）

```sql
-- 5.7 当前基线：相关子查询
SELECT r.stcd, r.tm, r.z
FROM st_river_r r
WHERE r.tm = (
      SELECT MAX(r2.tm) FROM st_river_r r2
      WHERE r2.stcd = r.stcd
        AND r2.tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)
)
  AND r.tm >= DATE_SUB(NOW(), INTERVAL 7 DAY);   -- 分区表必带 tm 范围
```

```sql
-- 8.0+ 现代写法（升级/迁移后更简洁）
SELECT * FROM (
    SELECT stcd, tm, z,
           ROW_NUMBER() OVER (PARTITION BY stcd ORDER BY tm DESC) AS rn
    FROM st_river_r
    WHERE tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)
) t WHERE rn = 1;
```

### 2.2 排名：各站水位高低（替代 `RANK() OVER(ORDER BY z DESC)`）

```sql
-- 5.7：相关子查询计数法（O(n²)，站多时慢，建议加 LIMIT 收窄）
SELECT a.stcd, a.z,
       (SELECT COUNT(*) + 1 FROM st_river_r b
        WHERE b.z > a.z
          AND b.tm >= DATE_SUB(NOW(), INTERVAL 1 DAY)) AS z_rank
FROM st_river_r a
WHERE a.tm >= DATE_SUB(NOW(), INTERVAL 1 DAY)
ORDER BY z_rank
LIMIT 20;
```

### 2.3 差分：逐条水位变化（替代 `LAG(z) OVER(PARTITION BY stcd ORDER BY tm)`）

```sql
-- 5.7：自连接找"上一条"
SELECT cur.stcd, cur.tm, cur.z,
       ROUND(cur.z - prev.z, 2) AS z_change
FROM st_river_r cur
LEFT JOIN st_river_r prev
  ON prev.stcd = cur.stcd
 AND prev.tm = (SELECT MAX(tm) FROM st_river_r p
                WHERE p.stcd = cur.stcd AND p.tm < cur.tm)
WHERE cur.stcd = '50801450'                       -- 目标站码
  AND cur.tm >= DATE_SUB(NOW(), INTERVAL 3 DAY)
ORDER BY cur.tm;
```

### 2.4 每日最高/最低（替代 `FIRST_VALUE … OVER(PARTITION BY DATE(tm) ORDER BY z DESC)`）

```sql
-- 5.7：GROUP BY 直接聚合（取值容易，取"发生时间"需再 JOIN）
SELECT DATE(tm) AS dt, MAX(z) AS z_max, MIN(z) AS z_min
FROM st_river_r
WHERE stcd = '50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(tm)
ORDER BY dt;
```

### 2.5 移动平均 / 累计求和（5.7 无窗口 → SQL 取数 + pandas）

> 5.7 下用用户变量 `@rn`/`@s` 模拟窗口函数**排序不可靠**（优化器可能重排求值顺序），**不建议**。
> 务实做法：SQL 取逐日聚合，pandas 算滚动/累计。

```python
import pandas as pd
from db import query

# SQL 只取每日均值（5.7 可跑），滚动计算交给 pandas
rows = query("""SELECT DATE(tm) AS dt, AVG(z) AS z_avg
                FROM st_river_r
                WHERE stcd = '50801450'
                  AND tm >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(tm)
                ORDER BY dt""")
df = pd.DataFrame(rows)
df['ma_7d']  = df['z_avg'].astype(float).rolling(7,  min_periods=1).mean()
df['cum_drp']= df['z_avg'].astype(float).cumsum()           # 累计（演示）
```

```sql
-- 8.0+ 现代写法（纯 SQL 滚动平均）
SELECT stcd, tm, z,
       AVG(z) OVER (PARTITION BY stcd ORDER BY tm
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS z_ma_7d
FROM st_river_r
WHERE stcd = '50801450' AND tm >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```

### 2.6 集合操作：交集 / 差集（5.7 无 INTERSECT/EXCEPT）

> `INTERSECT`/`EXCEPT` 是 MySQL **8.0.31+** 特性。5.7 用 JOIN 子查询替代。

```sql
-- 交集（INTERSECT 的 5.7 等价写法）：河道站 ∩ 水质站
SELECT COUNT(*) FROM (
   SELECT DISTINCT stcd FROM st_river_r WHERE tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)
) a JOIN (SELECT DISTINCT stcd FROM sl325.wq_pcp_d) b ON a.stcd = b.stcd;

-- 差集（EXCEPT 的 5.7 等价写法）：在 a 但不在 b
SELECT a.stcd FROM (SELECT DISTINCT stcd FROM 表A) a
LEFT JOIN (SELECT DISTINCT stcd FROM 表B) b ON a.stcd = b.stcd
WHERE b.stcd IS NULL;
```

## 3. MySQL 族内部差异（TiDB / OceanBase）

| 项 | MySQL 5.7/8.0 | TiDB | OceanBase(MySQL模式) |
|----|---------------|------|------|
| 窗口函数 / CTE | 8.0+ | ✅（兼容 8.0 语法） | ✅ |
| `LIMIT` / `DATE_SUB` / `IFNULL` | ✅ | ✅ | ✅ |
| 分区表语法 | `PARTITION BY RANGE` | 无分区（自动 region） | 有分区 |
| 存储过程 / 触发器 | ✅ | 有限 | ✅ |
| 连接 | pymysql | pymysql | pymysql |

> TiDB/OceanBase(MySQL 模式) 大多数 `sql_patterns.md` 写法可直接复用；分区裁剪语义不同（TiDB 无显式分区，OceanBase 有），但 `WHERE tm >= …` 习惯不变。

## 4. MySQL 5.7 → 8.0 升级检查清单

升级后这些会**立刻**影响现有脚本与连接，务必逐项排查：

- [ ] **认证插件（最常见的坑）**：8.0 默认 `caching_sha2_password`，旧 mysql 客户端 / 老 pymysql 会连接失败。
      - 解法 A：`pip install cryptography`（pymysql ≥0.9.3 依赖它支持 caching_sha2）。
      - 解法 B：`ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY '...';`（回退到旧插件）。
      - 检查：`lib/db.py` 连接是否报 "RuntimeError: cryptography is required" 或 auth plugin 错。
- [ ] **`sql_mode` 默认更严**：8.0 默认含 `ONLY_FULL_GROUP_BY`（5.7 默认不含）→ `SELECT` 非聚合列不在 `GROUP BY` 会报错。审计所有 `GROUP BY` 查询。
      - 临时查：`SELECT @@sql_mode;`
- [ ] **新增保留字**：8.0 把 `RANK`、`GROUPS`、`SYSTEM`、`CUME_DIST`、`NTILE` 等列为保留字 → 若有同名列/别名需加反引号。
- [ ] **字符集排序规则**：8.0 默认 `utf8mb4_0900_ai_ci`，5.7 默认 `utf8mb4_general_ci` → 跨库 `JOIN`/比较可能因排序规则冲突报 "Illegal mix of collations"。统一显式声明。
- [ ] **可借力的新特性**：窗口函数、CTE、`LATERAL`、`JSON_TABLE` —— 升级后把 `sql_patterns.md` 的"5.7 当前基线"写法逐步切到"8.0+ 现代写法"。
- [ ] **回归**：升级后用 `python3 scripts/evaluate_skills.py --validate-sql` 重跑全部预期 SQL，确认 98 条仍可执行。

## 5. 连接与驱动

| 目标 | Python 驱动 | `lib/db.py` 改动 |
|------|------------|----------------|
| MySQL 5.7（当前） | `pymysql` | 无需改（现状） |
| MySQL 8.0 | `pymysql` + `cryptography` | 连接参数不变；`pip install cryptography` |
| TiDB / OceanBase(MySQL) | `pymysql` | 仅改 host/port |
| PG 族 / Oracle 族 | `psycopg2` / `dmPython` | 需按 `DB_DIALECT` 切驱动（规划中） |

# SQL 安全规则

> 所有水利 skill 通用安全规则。每个 skill 的 Workflow 必须在执行 SQL 前遵循以下规则。

## 基本规则

- **只允许** SELECT / SHOW / DESCRIBE 语句
- **严禁** INSERT / UPDATE / DELETE / DROP / ALTER / TRUNCATE / CREATE / RENAME
- **严禁** INTO OUTFILE / LOAD DATA INFILE / LOAD_FILE()
- **严禁** 访问 mysql / information_schema / performance_schema 之外的系统库

## 运行时语法硬约束（违反 = 执行报错，必返空）

> 以下由 `db.py` 运行时强制，**不是建议**。违反直接导致 SQL 报错、返回空结果。

- **禁止 CTE / `WITH ... AS`** — 运行时只放行以 `SELECT` 开头的语句，CTE 会被拒绝。
  需要中间结果时**改用子查询**（derived table）：
  ```sql
  -- ❌ 禁止
  WITH latest AS (SELECT stcd, MAX(tm) mt FROM t GROUP BY stcd) SELECT ...
  -- ✅ 改用子查询
  SELECT ... FROM t JOIN (SELECT stcd, MAX(tm) mt FROM t GROUP BY stcd) latest
         ON t.stcd = latest.stcd AND t.tm = latest.mt
  ```
- **含单位/特殊字符的列别名必须加引号** — 别名里的 `()` `／` `³` 等会被 MySQL 当函数/语法错。
  ```sql
  -- ❌ 报错：near '(m)'
  SELECT r.z AS 水位(m), ROUND(r.z - rv.WRZ, 2) AS 超警戒(m) FROM ...
  -- ✅ 加单引号
  SELECT r.z AS '水位(m)', ROUND(r.z - rv.WRZ, 2) AS '超警戒(m)' FROM ...
  ```
- **禁止使用不存在的列** — 常见幻觉列：`st_stbprp_b.addvnm`（区域名称，**不存在**，只有 `addvcd` 行政区划码）、`st_stbprp_b.area`、`st_stbprp_b.region`。需要区域名时只能用 `addvcd` 码，或 JOIN 行政区划字典表。


## 性能安全规则

- **禁止无 WHERE 条件的全表扫描** — 必须包含时间范围或测站过滤条件
- **JOIN 必须有 ON 条件** — 禁止笛卡尔积（CROSS JOIN 无 ON）
- **子查询嵌套不超过 3 层**
- **大数据量查询必须加 LIMIT** — 默认 LIMIT 1000
- **st_rvfcch_b 无索引** — JOIN 时注意该表会全表扫描，避免多次 JOIN 该表
- **分区表注意** — st_river_r / st_was_r / st_pump_r / st_pump_pa 按 tm 做 RANGE 分区，WHERE 条件应包含 tm 范围以利用分区裁剪

## 检查方法

在执行 SQL 前，快速自查：
1. SQL 是否只包含 SELECT/SHOW/DESCRIBE？
2. 是否有 WHERE 条件（特别是时间范围）？
3. 每个 JOIN 是否都有 ON 条件？
4. 是否加了合理的 LIMIT？

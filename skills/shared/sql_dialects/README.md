# SQL 方言与可移植层

> 当前生产库：**MySQL 5.7.32**（192.168.100.103）。本目录按"兼容族"组织 SQL 方言差异，
> 服务两个目标：
> 1. 让 `shared/sql_patterns.md` 的写法在**当前 5.7 上能跑**（5.7 不支持窗口函数/CTE/LATERAL）；
> 2. 为**未来升级 MySQL 8 或迁移国产数据库**（达梦/人大金仓/OceanBase/GaussDB/TiDB）做准备。

## 为什么按"族"而非按"产品"组织

国产数据库按血缘分三类，同族语法高度互通，不必逐产品写文档：

| 族 | 代表产品 | 血缘 | 窗口函数/CTE | `LIMIT n` | Python 驱动 |
|----|---------|------|:---:|:---:|------|
| **MySQL 族** | MySQL 5.7 / 8.0+、TiDB、OceanBase(MySQL模式) | MySQL | 5.7 ❌ / 余 ✅ | ✅ | `pymysql` / `mysqlclient` |
| **PG 族** | PostgreSQL、人大金仓 KingbaseES、华为 GaussDB、openGauss | PostgreSQL | ✅ | ✅ | `psycopg2` |
| **Oracle 族** | 达梦 DM8、OceanBase(Oracle模式)、GaussDB(Oracle兼容) | Oracle | ✅ | ❌（用 `ROWNUM` / `FETCH FIRST`） | `dmPython` / `cx_Oracle` |

> 选族口诀：**产品决定族，族决定写法**。例如要迁达梦 → 查 Oracle 族；迁人大金仓 → 查 PG 族。

## 当前基线 vs 现代基线

- **当前基线 = MySQL 5.7.32**：不支持窗口函数（`ROW_NUMBER`/`LAG`/`OVER`）、CTE（`WITH`）、`LATERAL`、`JSON_TABLE`。
- **现代基线 = MySQL 8.0+ 或 PG/Oracle 族**：三者均支持窗口函数与 CTE。
- ⇒ `sql_patterns.md` 采用**双写法**：每个分析模式先给"5.7 可跑"写法，再给"8.0+/现代"写法并标注。

## 如何使用

1. 写新查询前，先查 `sql_patterns.md` 找对应模式的 **"当前基线（5.7）"** 写法。
2. 若某模式在 5.7 下无法用纯 SQL 表达（如移动平均、累计求和），按标注走 **"SQL 取数 → pandas 计算"**。
3. 升级或迁移时，按对应族文件的**迁移检查清单**审计全部 SQL（见 `mysql_family.md` 第 4 节）。
4. 连接驱动：`lib/db.py` 规划按 `DB_DIALECT` 环境变量切换（`mysql` → pymysql，`pg` → psycopg2，`dm` → dmPython）。

## 跨族可移植矩阵（速查）

| 需求 | MySQL 5.7 | MySQL 8.0+ | PG 族 | Oracle 族 |
|------|-----------|-----------|-------|-----------|
| 取每站最新记录（去重） | 相关子查询 | `ROW_NUMBER() OVER` | `ROW_NUMBER` / `DISTINCT ON` | `ROW_NUMBER` / `ROWNUM` |
| 当前时间 | `NOW()` / `CURDATE()` | 同 | `CURRENT_TIMESTAMP` / `now()` | `SYSDATE` |
| 最近 N 天 | `tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)` | 同 | `tm >= NOW() - INTERVAL '7 days'` | `tm >= SYSDATE - 7` |
| 字符串拼接 | `CONCAT(a,b)` | 同 | `a \|\| b` | `a \|\| b` |
| NULL 兜底 | `IFNULL(a,b)` | `IFNULL` | `COALESCE` | `NVL` |
| Top-N | `ORDER BY ... LIMIT n` | 同 | `LIMIT n` / `FETCH FIRST n ROWS ONLY` | `FETCH FIRST n ROWS ONLY` / `ROWNUM<=n` |
| 大小写不敏感模糊 | `LOWER(x) LIKE` | 同 | `ILIKE` | `UPPER(x) LIKE` |
| 取年份 | `YEAR(tm)` | 同 | `EXTRACT(YEAR FROM tm)` | `EXTRACT(YEAR FROM tm)` |
| 布尔 | 无（`TINYINT(1)`） | 同 | `BOOLEAN` | `NUMBER(1)` |
| 双引号 | 字符串字面量 | 同 | **标识符**（列名） | **标识符** |

> ⚠️ **双引号是最隐蔽的迁移坑**：MySQL 把 `"abc"` 当字符串，PG/Oracle 把它当列名。跨族迁移时字符串一律改单引号。

## 文件清单

| 文件 | 内容 | 状态 |
|------|------|------|
| `README.md`（本文件） | 族划分 + 跨族速查矩阵 | ✅ |
| `mysql_family.md` | MySQL 5.7 vs 8.0 差异 + 5.7 窗口函数替代写法 + 升级检查清单 | ✅ |
| `pg_family.md` | PG 族（PG/金仓/GaussDB）差异与从 MySQL 迁移要点 | 🚧 占位 |
| `oracle_family.md` | Oracle 族（达梦/OceanBase Oracle）差异与迁移要点 | 🚧 占位 |

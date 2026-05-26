# SQL 安全规则

> 所有水利 skill 通用安全规则。每个 skill 的 Workflow 必须在执行 SQL 前遵循以下规则。

## 基本规则

- **只允许** SELECT / SHOW / DESCRIBE 语句
- **严禁** INSERT / UPDATE / DELETE / DROP / ALTER / TRUNCATE / CREATE / RENAME
- **严禁** INTO OUTFILE / LOAD DATA INFILE / LOAD_FILE()
- **严禁** 访问 mysql / information_schema / performance_schema 之外的系统库

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

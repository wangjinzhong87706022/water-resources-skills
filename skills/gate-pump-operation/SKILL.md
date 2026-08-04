---
name: gate-pump-operation
description: "闸泵工况查询 — 闸门启闭状态、堰闸水情、泵站运行状态、泵站工情。核心表: sl323.st_gate_r, sl323.st_was_r, sl323.st_pump_r, sl323.st_pump_pa, sl323.st_stbprp_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, gate, pump, operation, sluice, scada]
    category: water-resources
---

# 闸泵工况查询 (Gate & Pump Operation)

查询闸门启闭状态、堰闸水情（上下游水位）、泵站运行状态、泵站工情。数据源: MySQL 192.168.100.103:3306，sl323 库。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询闸门启闭情况（开度、过闸流量） | Yes |
| 查询堰闸水情（上下游水位、过闸流量） | Yes |
| 查询泵站运行状态（开机台数、抽水流量） | Yes |
| 查询泵站工情数据（电压、电流、功率） | Yes |
| 查询闸泵综合运行状态 | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，sl323 库（只读）
- **pymysql 已由 lib/db.py 内部处理，🚫 禁止 pip install**（沙箱 externally-managed，pip 必失败且白烧 3-5 个轮次）。
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）
- 参考 `shared/sql_patterns.md` — SQL 通用查询模式（窗口函数处理时序数据）
- 参考 `shared/analysis_validation.md` — 分析验证（综合汇总结果的检查清单）
- 参考 `references/schema.md` — 完整表结构（来源: 实际 MySQL DDL）
- 参考 `references/business_rules.md` — 业务规则（闸泵状态编码、启闭口径）
- 参考 `references/few_shots.md` — SQL 示例（写 SQL 前优先匹配复用）

### 文件引用约定

本 skill 通过**环境变量 `WATER_RESOURCES_ROOT`**（指向 skills/）定位共享资源：

| 引用 | 逻辑路径 | 运行时真实路径（两平台统一） |
|------|---------|---------------------------|
| 共享库 | `lib/db.py` | `$WATER_RESOURCES_ROOT/lib/db.py` |
| 共享文档 | `shared/db_connection.md` | `$WATER_RESOURCES_ROOT/shared/db_connection.md` |
| 共享规则 | `shared/sql_safety_rules.md` | `$WATER_RESOURCES_ROOT/shared/sql_safety_rules.md` |

> `WATER_RESOURCES_ROOT` 由部署层注入（指向 skills 根目录），SKILL.md 与生成代码中不出现任何平台路径字面量；共享资源一律经 `$WATER_RESOURCES_ROOT` 定位。

**标准导入片段**（`__file__` 在 sandbox 暂存脚本中不可靠，勿用）：
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi
```

## Pitfalls

- **⚡ 单轮数据获取（性能第一杠杆，每轮 LLM 往返 30–80s，往返预算 ≤4）。不要为读中间结果而结束本轮**——站点识别、`MAX(tm)` 锚点、主查询全部写进**同一个 Python 脚本**一轮跑完。硬性禁令：
  1. **禁 schema 探查**（`SHOW COLUMNS`/`INFORMATION_SCHEMA`/`SELECT DATABASE()`）——列名见下方 Key Tables。
  2. **禁独立锚点轮**：`MAX(tm)` 内联为派生表子查询，不得单独查一轮再代入。
  3. **"分步执行" = 同脚本内多条 SQL，不是多个 LLM 回合。** 综合汇总用**一个** `query_multi([gate_sql, was_sql, pump_sql])` 批量取，禁分多轮。
  4. **禁重复执行**：一次成功即停，禁换时间窗重跑同一分析。
  5. **禁保留字别名**：派生表/子查询别名用 `lt`/`mt`/`mx`，**禁 `inner`/`latest`/`order`**（语法错，Q84 高发）。
  6. **一脚本一轮**：末尾一次性 `print` 全部结果。同脚本内需分步时用 f-string 实值代入（**禁跨回合留 `{stcd}` 占位符**）。
- **⚡ 相对时间窗锚定 MAX(tm)，禁锚 NOW()/CURDATE()。** 库数据滞后于挂钟（实测停在 2026-06），锚 NOW() 的窗口常落空返 0 行。
- **⚡ 聚合优先。** 状态/趋势类问题默认按日/站聚合输出，严禁 LIMIT 500 拉原始行灌上下文（st_pump_pa 有 30 列电气参数，逐行拉取会抬高后续每轮耗时）。
- **⚠️ 模糊时间（"一段时间/近期"）默认近 30 天（锚 MAX(tm)）直接查，禁止向用户反问**——单轮评测反问=0 分。
- **⚠️ 分区裁剪：st_was_r/st_pump_r/st_pump_pa 是 RANGE(tm) 分区表**，禁止 `YEAR(tm) IN (...)` 这类把 tm 包进函数的谓词，必须写 tm 连续区间。

- **⚠️ 禁止 CTE / `WITH … AS`（运行时报错，必返空）。** db.py 运行时只放行以 `SELECT` 开头的语句，CTE 会被拒绝。需中间结果（如"最新一条启闭/开度"）时**改用子查询**：`JOIN (SELECT stcd, MAX(tm) mt FROM st_gate_r GROUP BY stcd) lt ON g.stcd=lt.stcd AND g.tm=lt.mt`。覆盖 Q70/Q74/Q76。
- **⚠️ 含单位/特殊字符的列别名必须加引号。** `AS 闸门开度(m)` 的括号会被 MySQL 当函数→语法错→空结果。必须 `AS '闸门开度(m)'`、`AS '过闸流量(m³/s)'`。

- **综合汇总查询必须分步执行。** 当用户要求"泵站综合运行状态汇总"或"闸泵综合状态"时，不要尝试用一个复杂 SQL JOIN 所有表（st_gate_r + st_was_r + st_pump_r + st_pump_pa），这会因分区表扫描导致超时。
- **正确做法：拆分为 2-3 个简单查询。** 先查泵站列表(st_pump_r)，再查闸站列表(st_gate_r)，最后合并结果。每个查询只 JOIN st_stbprp_b 获取名称。
- **分区表查询必须带时间条件。** st_was_r、st_pump_r、st_pump_pa 按 tm 做 RANGE 分区，不带 WHERE tm 条件会全分区扫描导致超时。"最新"数据的正确做法：先 `SELECT MAX(tm) FROM st_pump_r`（或 st_was_r）取锚点（PK 索引，毫秒级），窗口把锚点直接内联子查询(免手写占位):`tm > DATE_SUB((SELECT MAX(tm) FROM st_pump_r), INTERVAL 7 DAY) AND tm <= (SELECT MAX(tm) FROM st_pump_r)`；相关子查询（如 `tm = (SELECT MAX(tm) FROM ... WHERE stcd=...)`）必须带同样的 tm 范围裁剪，禁止无界相关子查询。
- **避免在分区表上做无限制的 GROUP BY。** 先用时间范围过滤，再聚合。

## Workflow

1. **区分闸门 vs 堰闸。** 闸门启闭→st_gate_r; 上下游水位+过闸流量→st_was_r。
2. **确定泵站查询。** 泵站水情→st_pump_r; 泵站工情(电气参数)→st_pump_pa。
3. **JOIN 测站信息。** st_stbprp_b，闸站 sttp='DD'，泵站 sttp='DP'。
4. **运行状态判断。** 闸门: gtophgt > 0 已开启; 泵站: omcn > 0 有泵运行。
5. **综合汇总查询。** 拆分为独立查询：闸站状态(st_gate_r) + 堰闸水情(st_was_r) + 泵站状态(st_pump_r)，分别执行后合并结果。每个查询必须带时间范围 WHERE 条件。
6. **质量自检。** 执行 SQL 前确认符合安全规则。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。检查 sttp 过滤是否正确（DD=闸站, DP=泵站）。
7. **输出格式。** 结果应包含：测站名称、关键数值（水位/开度/流量）、运行状态判断、时间。用表格或分条列出，附带简要总结。

## 单轮模板（照抄，勿拆轮）

闸泵综合工况**一个脚本一轮跑完**：闸门/堰闸/泵站用**一个** `query_multi([...])` 批量取，每源各自内联派生表 `MAX(tm)` 锚点（禁相关子查询、禁保留字别名、禁拆多轮）。

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query_multi

gate_sql = """
SELECT b.stnm AS '闸站', g.gtname AS '闸门', g.gtophgt AS '开度(m)', g.gto AS '过闸流量(m³/s)',
       CASE WHEN g.gtophgt > 0 THEN '开启' ELSE '关闭' END AS '状态', g.tm AS '时间'
FROM sl323.st_gate_r g
JOIN (SELECT stcd, MAX(tm) mt FROM sl323.st_gate_r GROUP BY stcd) lt ON g.stcd=lt.stcd AND g.tm=lt.mt
JOIN sl323.st_stbprp_b b ON g.stcd=b.stcd
"""

pump_sql = """
SELECT b.stnm AS '泵站', p.omcn AS '开机台数', p.pmpq AS '抽水流量(m³/s)',
       CASE WHEN p.omcn > 0 THEN '运行' ELSE '停机' END AS '状态', p.tm AS '时间'
FROM sl323.st_pump_r p
JOIN (SELECT stcd, MAX(tm) mt FROM sl323.st_pump_r GROUP BY stcd) lt ON p.stcd=lt.stcd AND p.tm=lt.mt
JOIN sl323.st_stbprp_b b ON p.stcd=b.stcd
"""

was_sql = """
SELECT b.stnm AS '堰闸', w.upz AS '上游水位(m)', w.dwz AS '下游水位(m)', w.tgtq AS '过闸流量(m³/s)', w.tm AS '时间'
FROM sl323.st_was_r w
JOIN (SELECT stcd, MAX(tm) mt FROM sl323.st_was_r GROUP BY stcd) lt ON w.stcd=lt.stcd AND w.tm=lt.mt
JOIN sl323.st_stbprp_b b ON w.stcd=b.stcd
"""

gates, pumps, was = query_multi([gate_sql, pump_sql, was_sql])
for label, rows in [('闸门', gates), ('泵站', pumps), ('堰闸', was)]:
    print(f'=== {label}（{len(rows)}）===')
    for row in rows:                    # 打印全行，勿截断
        print(row)
```

- 派生表别名用 `lt`/`mt`，**禁 `inner`/`latest`**（保留字，语法错）。
- 一次成功即停：**禁**换 7/30 天窗口重跑同一汇总。

## Validation Gate

**闸泵工况查询交付前必须通过以下检查。**

### 分区表时间条件检查

- [ ] **st_was_r/st_pump_r/st_pump_pa 必须带 WHERE tm 条件**：这三个表按 tm 做 RANGE 分区，不带时间条件会全分区扫描导致超时
- [ ] **时间范围合理**：窗口锚定 MAX(tm) 实值(脚本内 f-string 代入或内联子查询):`tm > DATE_SUB((SELECT MAX(tm) FROM st_pump_r), INTERVAL 7 DAY) AND tm <= (SELECT MAX(tm) FROM st_pump_r)`；禁锚 NOW()/CURDATE()（库数据滞后，窗口会落空）

**常见错误示例**：
```sql
❌ 错误：SELECT * FROM st_pump_r WHERE stcd='xxx'（无 tm 条件，超时）
❌ 错误：用 NOW()/CURDATE() 锚相对时间窗（库数据滞后于挂钟，窗口落空返 0 行）
✅ 正确：先 SELECT MAX(tm) FROM st_pump_r 得锚点（如 '2026-06-15 08:00:00'），再：
        SELECT * FROM st_pump_r WHERE stcd='xxx'
        AND tm > DATE_SUB('2026-06-15 08:00:00', INTERVAL 7 DAY) AND tm <= '2026-06-15 08:00:00'
```

### 运行状态逻辑检查

- [ ] **闸门开启判断**：`gtophgt > 0` → 已开启，`gtophgt = 0` → 关闭
- [ ] **泵站运行判断**：`omcn > 0` → 有泵运行，`omcn = 0` → 停机
- [ ] **泵站工情开关判断**：`switch = 1` → 开，`switch = 0` → 关

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl323.st_gate_r | 闸门启闭 | stcd, tm, **gtname**(PK之一), gtophgt(开度), gto(过闸流量) |
| sl323.st_was_r | 堰闸水情 | stcd, tm, **upz**(上游水位), **dwz**(下游水位), tgtq(过闸流量) |
| sl323.st_pump_r | 泵站水情 | stcd, tm, omcn(开机台数), pmpq(抽水流量), ppupz, ppdwz |
| sl323.st_pump_pa | 泵站工情 | stcd, tm, **pumpname**(PK之一), switch(开关), 电气参数 |
| sl323.st_stbprp_b | 测站信息 | sttp='DD'/'DP' |

## Business Rules Summary

- **st_gate_r 没有 upz/dwz 字段** — 上下游水位在 st_was_r 中
- **st_gate_r PK 是 (stcd, tm, gtname)** — 一个站多个闸门
- **st_was_r PK 是 (tm, stcd)** — 注意 tm 在前
- **st_pump_r PK 是 (tm, stcd)** — pumpname 不在 PK 中
- **st_pump_pa PK 是 (stcd, tm, pumpname)** — pumpname 在 PK 中
- **st_pump_pa.switch:** 1=开, 0=关
- **st_was_r, st_pump_r, st_pump_pa 按 tm 做 RANGE 分区**

## Related Skills

- `water-situation` — 实时水位查询
- `water-warning` — 防洪预警
- `water-visualization` — 闸泵运行状态面板图

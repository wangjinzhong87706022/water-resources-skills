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
- **pymysql:** execute_code 环境可能未安装，首次使用需先运行 `pip install pymysql`
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）
- 参考 `shared/sql_patterns.md` — SQL 通用查询模式（窗口函数处理时序数据）
- 参考 `shared/analysis_validation.md` — 分析验证（综合汇总结果的检查清单）

## Pitfalls

- **综合汇总查询必须分步执行。** 当用户要求"泵站综合运行状态汇总"或"闸泵综合状态"时，不要尝试用一个复杂 SQL JOIN 所有表（st_gate_r + st_was_r + st_pump_r + st_pump_pa），这会因分区表扫描导致超时。
- **正确做法：拆分为 2-3 个简单查询。** 先查泵站列表(st_pump_r)，再查闸站列表(st_gate_r)，最后合并结果。每个查询只 JOIN st_stbprp_b 获取名称。
- **分区表查询必须带时间条件。** st_was_r、st_pump_r、st_pump_pa 按 tm 做 RANGE 分区，不带 WHERE tm 条件会全分区扫描导致超时。"最新"数据用 `WHERE tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)` 或子查询 `WHERE tm = (SELECT MAX(tm) FROM ...)` 限定范围。
- **避免在分区表上做无限制的 GROUP BY。** 先用时间范围过滤，再聚合。

## Workflow

1. **区分闸门 vs 堰闸。** 闸门启闭→st_gate_r; 上下游水位+过闸流量→st_was_r。
2. **确定泵站查询。** 泵站水情→st_pump_r; 泵站工情(电气参数)→st_pump_pa。
3. **JOIN 测站信息。** st_stbprp_b，闸站 sttp='DD'，泵站 sttp='DP'。
4. **运行状态判断。** 闸门: gtophgt > 0 已开启; 泵站: omcn > 0 有泵运行。
5. **综合汇总查询。** 拆分为独立查询：闸站状态(st_gate_r) + 堰闸水情(st_was_r) + 泵站状态(st_pump_r)，分别执行后合并结果。每个查询必须带时间范围 WHERE 条件。
6. **质量自检。** 执行 SQL 前确认符合安全规则。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。检查 sttp 过滤是否正确（DD=闸站, DP=泵站）。
7. **输出格式。** 结果应包含：测站名称、关键数值（水位/开度/流量）、运行状态判断、时间。用表格或分条列出，附带简要总结。

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

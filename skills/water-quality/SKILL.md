---
name: water-quality
description: "水质综合查询 — 水质指标监测、水质等级评定（单因子评价法）、水质预测。核心表: sl325.wq_pcp_d, slztk.st_mx_preset_r_shj_auto, slztk.st_mx_taskid_shj_auto, slztk.wq_cod_pz, sl323.st_stbprp_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, quality, water-quality, monitoring, rating, forecast, CODMn, DO, NH3N, TP]
    category: water-resources
---

# 水质综合查询 (Water Quality)

查询水质监测指标、水质等级评定、水质预测。涉及 **三个库**: sl325(监测), slztk(预测), sl323(测站)。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询某测站水质指标（DO、CODMn、NH3N、TP、pH等） | Yes |
| 查询水质变化趋势 | Yes |
| 查询水质等级评定（单因子评价法） | Yes |
| 查询未来24小时水质预测及评级 | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，涉及三个库（只读）
  - sl325: wq_pcp_d（水质监测数据）
  - slztk: st_mx_preset_r_shj_auto, st_mx_taskid_shj_auto, wq_cod_pz（水质预测）
  - sl323: st_stbprp_b（测站信息）
- **pymysql 已由 lib/db.py 内部处理，🚫 禁止 pip install**（沙箱 externally-managed，pip 必失败且白烧 3-5 个轮次）。
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）
- 参考 `shared/statistical_methods.md` — 统计分析方法（趋势分析、异常检测、描述统计）
- 参考 `shared/sql_patterns.md` — SQL 通用查询模式（窗口函数、CTE 分步构建）
- 参考 `shared/analysis_validation.md` — 分析验证（质量检查清单、常见陷阱、置信度评定）
- 参考 `references/schema.md` — 完整表结构（来源: 实际 MySQL DDL）
- 参考 `references/business_rules.md` — 业务规则（水质评价标准、指标口径）
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

- **⚡ 单轮数据获取（性能第一杠杆，每轮 LLM 往返 30–80s，往返预算 ≤4）。不要为读中间结果而结束本轮**——站点识别、时间锚点、主查询全部写进**同一个 Python 脚本**一轮跑完（脚本内可多次 `query()`/`query_multi()`，同一轮零额外往返）。硬性禁令：
  1. **禁 schema 探查**：列名照抄下方/`references/schema.md`，不得 `SHOW COLUMNS`/`INFORMATION_SCHEMA`/`SELECT DATABASE()`。
  2. **禁独立锚点轮**：`MAX(spt)`/最新 `taskid` 一律内联为**子查询**，不得单独查一轮再代入下一轮。
  3. **禁站点/taskid 独立发现轮**：用 `stnm LIKE` 派生表 JOIN 内联（`rvnm` 常 NULL → `(stnm LIKE '%X%' OR rvnm LIKE '%X%')`）。
  4. **禁重复执行**：一次成功即停，不得换时间窗重跑同一分析。
  5. **一脚本一轮**：末尾一次性 `print` 结果（含绘图所需数据）。
- **📋 wq_pcp_d 已知列（免探查）**：`stcd, spt(采样时间,PK), dox, codmn, nh3n, tp, ph, wtmp, turb, cond`；时间字段是 **spt** 不是 tm。
- **⚡ 聚合优先。** 水质"趋势/变化"类问题默认按日/周聚合指标均值（`GROUP BY DATE(spt)` + `AVG(...)`），**禁止拉原始行**再自行汇总。
- **⚠️ 时间范围缺省时用默认值直接查，禁止反问（高频 0 分）。** "一段时间内/近期/最近"等模糊时间**不要**向用户追问时间范围——单轮场景下反问即任务失败。默认口径：**近 30 天**（锚定该表 `MAX(spt)` 而非 CURDATE，库数据可能滞后），"趋势"类可按周/月聚合。答复中注明所采用的时间窗即可。
- **⚠️ 含单位/特殊字符的列别名必须加引号。** `AS CODMn(mg/L)` 的括号/斜杠会触发 MySQL 语法错→空结果。必须 `AS 'CODMn(mg/L)'`、`AS '氨氮(mg/L)'`、`AS '溶解氧(mg/L)'`。
- **⚠️ 查"每站最新一条"严禁相关子查询 `d.spt = (SELECT MAX(spt) ... WHERE stcd = d.stcd)`（30s 必超时）。** wq_pcp_d 相关子查询逐行执行必超时（实测）。**必须**用派生表 JOIN（实测 0.1s）：
  ```sql
  FROM sl325.wq_pcp_d d
  JOIN (SELECT stcd, MAX(spt) AS maxSpt FROM sl325.wq_pcp_d GROUP BY stcd) m
    ON d.stcd = m.stcd AND d.spt = m.maxSpt
  ```
- **⚠️ 禁止 CTE / `WITH … AS`。** db.py 只放行 SELECT/SHOW/DESCRIBE/EXPLAIN 开头的语句，`WITH` 开头会被拒绝，改用子查询。
- **按河道名查测站必须双匹配。** `rvnm` 常为 NULL，须 `WHERE (stnm LIKE '%X%' OR rvnm LIKE '%X%')`。

## Workflow

1. **识别查询场景。** 历史监测→sl325.wq_pcp_d; 等级评定→CASE WHEN 6级标准; 水质预测→slztk.st_mx_preset_r_shj_auto。
2. **识别水质站。** sttp='WQ'，通过 stnm LIKE 匹配站点。
3. **水质评级。** 按 6 级标准（Ⅰ~劣Ⅴ）对各指标分级，取最差等级。**阈值是国标固定值，照抄下方模板 ③ 的 CASE WHEN，勿臆造**（GB 3838-2002）。
4. **水质预测。** 获取最新 taskid，type 映射（103=DO, 104=CODMn, 105=TP, 128=NH3N）。
5. **跨库查询需带库名前缀:** sl325.wq_pcp_d, slztk.st_mx_preset_r_shj_auto 等。
6. **质量自检。** 执行 SQL 前确认符合安全规则。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。返回数值做合理性检查（CODMn 0~50mg/L, DO 0~20mg/L）。
7. **统计增强（可选）。** 如需趋势分析或异常检测，参考 shared/statistical_methods.md（移动平均、IQR 异常检测、水质指标分布描述）。
8. **输出验证。** 交付前按 shared/analysis_validation.md 做置信度评定——特别是同比/环比结论的陷阱检查（不完整周期、分母漂移、均值之均值）。

## 单轮模板（照抄，勿拆轮）

> 站点/锚点全部内联，一个脚本一轮出结果。绘图所需数据在同脚本内一并 print。

**① 趋势/监测单轮模板**（近 30 天按日聚合；`spt` 锚定表内 `MAX(spt)`，勿用 NOW/CURDATE）：
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

STN = '瘦西湖'   # 改成目标站名
rows = query(f"""
  SELECT DATE(d.spt) AS '日期',
         ROUND(AVG(d.dox),2)   AS '溶解氧(mg/L)',
         ROUND(AVG(d.codmn),2) AS 'CODMn(mg/L)',
         ROUND(AVG(d.nh3n),3)  AS '氨氮(mg/L)',
         ROUND(AVG(d.tp),3)    AS '总磷(mg/L)',
         ROUND(AVG(d.ph),2)    AS 'pH',
         ROUND(AVG(d.wtmp),1)  AS '水温(℃)'
  FROM sl325.wq_pcp_d d
  JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
  WHERE b.sttp='WQ' AND (b.stnm LIKE '%瘦西湖%' OR b.rvnm LIKE '%瘦西湖%')  -- 换成目标水质站名
    AND d.spt > DATE_SUB((SELECT MAX(spt) FROM sl325.wq_pcp_d), INTERVAL 30 DAY)
  GROUP BY DATE(d.spt) ORDER BY DATE(d.spt)
""")
print(rows)   # 同轮内即可据此做统计/绘图，勿再发新查询
```

**② 水质预测单轮模板**（最新有效 `taskid` 内联为子查询，勿单独查一轮）：
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

STN = '瘦西湖'
rows = query(f"""
  SELECT b.stnm AS '测站', r.tm AS '预报时间', r.type, r.vals
  FROM slztk.st_mx_preset_r_shj_auto r
  JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
  WHERE b.sttp='WQ' AND (b.stnm LIKE '%瘦西湖%' OR b.rvnm LIKE '%瘦西湖%')  -- 换成目标水质站名
    AND r.type IN (103,104,105,128)
    AND r.tm BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
    AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_shj_auto
                    WHERE state='1' ORDER BY tm DESC LIMIT 1)
  ORDER BY r.tm
""")
print(rows)   # type 映射 103=DO 104=CODMn 105=TP 128=NH3N；同轮内评级
```

**③ 水质评级单轮模板（GB 3838-2002 单因子评价法，6 档 CASE WHEN 照抄）**：

> ⚠️ **评级阈值是国标固定值，禁止臆造**。下表为 GB 3838-2002 地表水 6 档标准，**综合水质等级 = 各指标评出的最差（最大）那档**（单因子评价法取最差，不取平均/众数）。
>
> | 指标(mg/L) | Ⅰ类 | Ⅱ类 | Ⅲ类 | Ⅳ类 | Ⅴ类 | 劣Ⅴ类 |
> |-----------|------|------|------|------|------|--------|
> | CODMn (≤) | 2 | 4 | 6 | 10 | 15 | >15 |
> | DO (≥) | 7.5 | 6 | 5 | 3 | 2 | <2 |
> | NH3N (≤) | 0.15 | 0.5 | 1 | 1.5 | 2 | >2 |
> | TP (≤) | 0.02 | 0.1 | 0.2 | 0.3 | 0.4 | >0.4 |
>
> 注：DO 越大越好（用 `>=`），CODMn/NH3N/TP 越小越好（用 `<=`）。查"劣于Ⅳ类"等**单档**问题，只需 Ⅳ 类边界：`CODMn>10 OR DO<3 OR NH3N>1.5 OR TP>0.3`。

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

STN = '京杭运河'   # 换成目标水质站名
rows = query(f"""
  SELECT b.stnm AS '测站', d.spt AS '采样时间',
         d.codmn AS 'CODMn', d.dox AS 'DO', d.nh3n AS 'NH3N', d.tp AS 'TP',
         CASE
           WHEN d.codmn <= 2 THEN 'Ⅰ类' WHEN d.codmn <= 4 THEN 'Ⅱ类'
           WHEN d.codmn <= 6 THEN 'Ⅲ类' WHEN d.codmn <= 10 THEN 'Ⅳ类'
           WHEN d.codmn <= 15 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
         END AS 'CODMn评级',
         CASE
           WHEN d.dox >= 7.5 THEN 'Ⅰ类' WHEN d.dox >= 6 THEN 'Ⅱ类'
           WHEN d.dox >= 5 THEN 'Ⅲ类' WHEN d.dox >= 3 THEN 'Ⅳ类'
           WHEN d.dox >= 2 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
         END AS 'DO评级',
         CASE
           WHEN d.nh3n <= 0.15 THEN 'Ⅰ类' WHEN d.nh3n <= 0.5 THEN 'Ⅱ类'
           WHEN d.nh3n <= 1 THEN 'Ⅲ类' WHEN d.nh3n <= 1.5 THEN 'Ⅳ类'
           WHEN d.nh3n <= 2 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
         END AS 'NH3N评级',
         CASE
           WHEN d.tp <= 0.02 THEN 'Ⅰ类' WHEN d.tp <= 0.1 THEN 'Ⅱ类'
           WHEN d.tp <= 0.2 THEN 'Ⅲ类' WHEN d.tp <= 0.3 THEN 'Ⅳ类'
           WHEN d.tp <= 0.4 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
         END AS 'TP评级'
  FROM sl325.wq_pcp_d d
  JOIN (SELECT stcd, MAX(spt) AS maxSpt FROM sl325.wq_pcp_d GROUP BY stcd) m
    ON d.stcd = m.stcd AND d.spt = m.maxSpt
  JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
  WHERE b.sttp='WQ' AND (b.stnm LIKE '%京杭运河%' OR b.rvnm LIKE '%京杭运河%')  -- 换成目标水质站名
""")
print(rows)   # 综合等级 = 上列四档中最差(最大序号)那档;同轮内输出,勿再发新查询
```

## Validation Gate

**水质查询交付前必须通过以下检查。**

### 水质评级检查

- [ ] **取最差等级**：单因子评价法必须取**最差等级**，不能取平均或多数等级
- [ ] **6 级标准正确性**：Ⅰ~劣Ⅴ 的划分阈值符合国标（GB 3838-2002）

**常见错误示例**：
```sql
❌ 错误：取出现次数最多的等级（多数原则）
✅ 正确：取最差等级（任一指标最差决定整体等级）
```

### 测站类型检查

- [ ] **水质站过滤正确**：sttp='WQ'，不能与水位站（ZZ）/水文站（ZQ）/水库站（RR）混淆
- [ ] **跨库 JOIN 测站类型验证**：JOIN sl323.st_stbprp_b 后确认 sttp='WQ'

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl325.wq_pcp_d | 水质监测 | stcd, **spt**(采样时间,PK), dox, codmn, nh3n, tp, ph, wtmp, turb, cond |
| slztk.st_mx_preset_r_shj_auto | 水质预测 | stcd, tm, **type**(int: 103/104/105/128), vals, taskid |
| slztk.st_mx_taskid_shj_auto | 水质预测任务 | **taskid**(PK), tm, **state**(0/1) |
| slztk.wq_cod_pz | CODMn转换 | min, max, **value**(decimal归一化值) |
| sl323.st_stbprp_b | 测站信息 | sttp='WQ' |

## Business Rules Summary

- **wq_pcp_d 时间字段是 spt**，不是 tm
- **水质站类型:** sttp='WQ'
- **st_mx_preset_r_shj_auto.type 是 int**，不是 varchar
- **st_mx_taskid_shj_auto 状态字段是 state**，不是 stuts
- **wq_cod_pz.value 是 decimal 归一化值**（0~100），不是等级名称
- **跨库查询:** wq_pcp_d 在 sl325，预测表在 slztk，测站表在 sl323

## Related Skills

- `water-warning` — 水质预警
- `water-situation` — 水位查询
- `water-visualization` — 水质指标趋势图、等级阶梯图

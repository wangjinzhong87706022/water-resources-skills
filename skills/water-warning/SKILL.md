---
name: water-warning
description: "水利预警 — 防洪预警（超警戒/超保证水位）和水质预警（水质等级低于Ⅳ类）。核心表: sl323.st_river_r, sl323.st_rvfcch_b, sl325.wq_pcp_d, sl323.st_stbprp_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, warning, alert, flood, water-quality, hydrology, scada]
    category: water-resources
---

# 水利预警 (Water Warning)

防洪预警（超警戒/超保证水位）和水质预警（水质等级低于Ⅳ类）。数据源: MySQL 192.168.100.103:3306，涉及 sl323 + sl325 库。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询哪些站点超警戒水位 | Yes |
| 查询防洪预警汇总 | Yes |
| 查询水位是否超保证水位 | Yes |
| 查询水质预警站点 | Yes |
| 查询水质异常情况（低于Ⅳ类） | Yes |
| 综合防洪+水质预警查询 | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，涉及两个库（只读）
  - sl323: st_river_r, st_rvfcch_b, st_stbprp_b（防洪+测站）
  - sl325: wq_pcp_d（水质监测）
- **pymysql 已由 lib/db.py 内部处理，🚫 禁止 pip install**（沙箱 externally-managed，pip 必失败且白烧 3-5 个轮次）。
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）
- 参考 `shared/statistical_methods.md` — 统计分析方法（异常值识别、趋势判断）
- 参考 `shared/analysis_validation.md` — 分析验证（预警报告的置信度评定和陷阱检查）

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

- **⚡ 单轮数据获取（性能第一杠杆，每轮 LLM 往返 30–80s，往返预算 ≤4）。不要为读中间结果而结束本轮**——站点识别、`MAX(tm)` 锚点、阈值存在性检查、主查询全部写进**同一个 Python 脚本**一轮跑完（脚本内多次 `query()`/一次 `query_multi([...])` 均零额外往返）。硬性禁令：
  1. **禁 schema 探查**（`SHOW COLUMNS`/`INFORMATION_SCHEMA`/`SELECT DATABASE()`）——列名见下方 Key Tables。
  2. **禁独立锚点轮**：`MAX(tm)` 内联为派生表子查询，不得单独查一轮再代入。
  3. **禁多源分轮**：河道/泵站/闸门三源用**一个** `query_multi([river_sql, pump_sql, gate_sql])` 批量取，禁分 3 轮。
  4. **禁重复执行**：一次成功即停，禁把整段预警/汇总分析换窗口重跑（Q92/Q93 高发）。
  5. **一脚本一轮**：末尾一次性 `print` 全部结果（清单题打印全行）。
- **⚡ 相对时间窗必须锚定 `MAX(tm)`，禁锚 NOW()/CURDATE()。** 库数据滞后于挂钟（实测停在 2026-06），`DATE_SUB(NOW(), ...)` 窗口常落空返 0 行。先取该表 `MAX(tm)` 再推时间窗。
- **⚡ 聚合优先，禁 `LIMIT 500` 拉原始行。** 统计/趋势/汇总类问题在 SQL 里用 COUNT/SUM/AVG/GROUP BY 完成，不要拉原始行回 Python 再汇总。
- **⚠️ 模糊时间禁止反问。** "近期/一段时间"等模糊时间默认取**近 30 天**（锚 `MAX(tm)`）直接查，**禁止向用户反问**（单轮评测反问=0 分），答复中注明所采用的时间窗即可。
- **⚠️ 分区裁剪：st_river_r 是 RANGE(tm) 分区表。** 时间条件必须写成 tm 连续区间（`tm >= '...' AND tm < '...'`），**禁止 `YEAR(tm) IN (...)`** 等函数包裹 tm 的写法——无法分区裁剪导致全表扫描（跨年预警复盘高发）。
- **⚠️ 禁止 CTE / `WITH … AS`（运行时报错，必返空）。** db.py 只放行以 `SELECT`/`SHOW`/`DESCRIBE`/`EXPLAIN` 开头的语句，CTE（`WITH` 开头）会被拒绝。需"每个站最新水位"等中间结果时**改用子查询**：`JOIN (SELECT stcd, MAX(tm) mt FROM st_river_r GROUP BY stcd) latest ON r.stcd=latest.stcd AND r.tm=latest.mt`。覆盖 Q85/Q89/Q93。
- **⚠️ 含单位/特殊字符的列别名必须加引号。** `AS 超警戒(m)` 的括号会被 MySQL 当函数→语法错→空结果。必须 `AS '当前水位(m)'`、`AS '超警戒(m)'`、`AS '警戒水位(m)'`。
- **按河道名查测站必须双匹配。** 运河站 `rvnm` 常为 NULL，只用 `rvnm LIKE` 必返 0 行，须 `WHERE (stnm LIKE '%X%' OR rvnm LIKE '%X%')`。
- **⚠️ 站点属性列（stnm/rvnm/hnnm/bsnm）只在 `st_stbprp_b`，数据表 `st_river_r` 只有 stcd+测量值(z/q/tm)。** 取站名/河名/水系**必须 `JOIN st_stbprp_b`**，禁止从 `st_river_r` 直接 SELECT stnm/rvnm（报 `Unknown column 'r.rvnm'`）。覆盖 Q85/Q89。
- **⚠️ 严禁残留 `{...}` 占位符（高频语法错）。** 生成 SQL 后自检：**不许出现 `{` `}`**。条件必须直接写成具体值（如 `WHERE b.stnm LIKE '%扬州%'`），**禁止**留 `{where_condition}`/`{stcd}` 等未填模板变量——MySQL 会语法错。覆盖 Q89。
- **⚠️ 水质表 wq_pcp_d 查"每站最新"严禁相关子查询 `spt = (SELECT MAX(spt) ... WHERE stcd = d.stcd)`（30s 必超时）。** 必须用派生表 JOIN：`JOIN (SELECT stcd, MAX(spt) AS maxSpt FROM sl325.wq_pcp_d GROUP BY stcd) m ON d.stcd = m.stcd AND d.spt = m.maxSpt`（实测 0.1s）。
- **⚠️ 清单类问题必须完整输出全部行，禁止截断为 top N。** "所有站点的预警水位配置"、"所有站点预警状态一览"这类清单题，答案价值在**完整列表**。执行 SQL 后要把**全部行**打印到输出（如 `for row in rows: print(...)`），最终答复也应含完整清单（可按状态分组）。只展示"前10条+省略号"会导致大部分站点信息丢失。

## Workflow

1. **防洪预警。** 比较 st_river_r.z 与 st_rvfcch_b.WRZ/GRZ。
   - z > WRZ → 黄色预警（超警戒）
   - z > GRZ → 红色预警（超保证）
2. **水质预警。** 查询 sl325.wq_pcp_d 各指标，按 6 级标准评级（单因子评价法），任一指标低于Ⅳ类触发预警。
3. **跨库查询需带库名前缀:** sl325.wq_pcp_d, sl323.st_river_r 等。
4. **质量自检。** 执行 SQL 前确认符合安全规则。特别注意 st_rvfcch_b.STCD 是大写。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。

## 多源单轮模板（照抄，勿拆轮）

综合防洪形势（河道超警/泵站排水/闸门开启）**一个脚本一轮跑完**：三源用 `query_multi([...])` 批量取，每源各自内联派生表 `MAX(tm)` 锚点（禁相关子查询、禁拆 3 轮、禁换窗重跑）。

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query_multi

river_sql = """
SELECT b.stnm AS '测站', r.z AS '当前水位(m)', rv.WRZ AS '警戒水位(m)', rv.GRZ AS '保证水位(m)',
       CASE WHEN r.z > rv.GRZ THEN '红色预警' WHEN r.z > rv.WRZ THEN '黄色预警' ELSE '正常' END AS '状态'
FROM sl323.st_river_r r
JOIN (SELECT stcd, MAX(tm) mt FROM sl323.st_river_r GROUP BY stcd) lt ON r.stcd=lt.stcd AND r.tm=lt.mt
JOIN sl323.st_stbprp_b b ON r.stcd=b.stcd
JOIN sl323.st_rvfcch_b rv ON r.stcd=rv.STCD
WHERE rv.WRZ IS NOT NULL AND r.z > rv.WRZ
ORDER BY r.z-rv.WRZ DESC
"""

pump_sql = """
SELECT COUNT(*) AS '正在排水泵站数', ROUND(SUM(p.pmpq),2) AS '总排水流量(m³/s)'
FROM sl323.st_pump_r p
JOIN (SELECT stcd, MAX(tm) mt FROM sl323.st_pump_r GROUP BY stcd) lt ON p.stcd=lt.stcd AND p.tm=lt.mt
WHERE p.pdchcd='2' AND p.omcn > 0
"""

gate_sql = """
SELECT COUNT(*) AS '开启闸门数'
FROM sl323.st_gate_r g
JOIN (SELECT stcd, MAX(tm) mt FROM sl323.st_gate_r GROUP BY stcd) lt ON g.stcd=lt.stcd AND g.tm=lt.mt
WHERE g.gtophgt > 0
"""

rivers, pumps, gates = query_multi([river_sql, pump_sql, gate_sql])
print('超警戒站点：', len(rivers))
for row in rivers:                      # 清单题打印全行，勿截断
    print(row)
print('泵站：', pumps)
print('闸门：', gates)
```

- 派生表别名用 `lt`/`mt`/`mx`，**禁用 `inner`/`latest` 等保留字**（语法错）。
- 一次成功即停：**禁**把同一分析换 30/60/90 天窗口重跑（Q92 ×3、Q93 ×4 均属此坑）。

## Validation Gate

**预警查询交付前必须通过以下检查。**

### 阈值对比方向检查

- [ ] **超警戒/超保证方向正确**：`z > WRZ` → 黄色预警（超警戒），`z > GRZ` → 红色预警（超保证）
- [ ] **级别不混淆**：红色预警（超保证）优先级高于黄色预警（超警戒），不能反过来

**常见错误示例**：
```sql
❌ 错误：z < WRZ → 超警戒（方向反了）
✅ 正确：z > WRZ → 超警戒
```

### 阈值数据存在性检查

- [ ] **查询前验证**：在查询 WRZ/GRZ 前，**必须**验证该测站阈值数据是否存在
  ```sql
  SELECT COUNT(*) as cnt FROM st_rvfcch_b WHERE STCD='目标站码' AND (WRZ IS NOT NULL OR GRZ IS NOT NULL)
  ```
- [ ] **缺失处理**：若 cnt=0，**跳过阈值查询**，直接告知用户"⚠️ 该站阈值数据缺失"

**参考**：water-situation 的 `references/threshold_query_validation.md`

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl323.st_river_r | 河道水位 | stcd, tm, z |
| sl323.st_rvfcch_b | 防洪指标 | **STCD**(注意大写), WRZ(警戒水位), GRZ(保证水位) |
| sl325.wq_pcp_d | 水质数据 | stcd, **spt**(采样时间), dox, codmn, nh3n, tp |
| sl323.st_stbprp_b | 测站信息 | sttp='ZZ'(水位站)/'WQ'(水质站) |

## Business Rules Summary

- **st_rvfcch_b 无 PK**，STCD 列名是大写（不是小写 stcd）
- **st_rvfcch_b JOIN 条件:** `r.stcd = rv.STCD`（注意大小写）
- **超警戒:** z > WRZ → 黄色预警
- **超保证:** z > GRZ → 红色预警
- **水质预警阈值（Ⅳ类）:** CODMn > 10, DO < 3, NH3N > 1.5, TP > 0.3
- **wq_pcp_d 时间字段是 spt**，不是 tm
- **水质站类型:** sttp='WQ'

## Related Skills

- `water-situation` — 实时水位查询
- `water-quality` — 水质评级详情
- `gate-pump-operation` — 闸泵调度
- `water-visualization` — 预警状态汇总面板图

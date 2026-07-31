---
name: rainfall
description: "雨情综合查询 — 实时降雨、降雨预报（短临/中长期）、区域降雨统计。核心表: sl323.st_pptn_r, sl323.f_rnfl_h, sl323.f_rnfl_info_r, sl323.st_stbprp_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, rainfall, precipitation, forecast, hydrology, scada]
    category: water-resources
---

# 雨情综合查询 (Rainfall)

查询实时降雨量、降雨预报、区域降雨统计。数据源: MySQL 192.168.100.103:3306/sl323。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询某测站/区域实时降雨量 | Yes |
| 查询扬州城区降雨总量（固定 stcd='58245'） | Yes |
| 查询最大降雨日期 | Yes |
| 查询未来降雨预报（短临/中长期） | Yes |
| 查询各区域累计降雨量排名 | Yes |
| 查询某测站最近N天降雨数据 | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，数据库 sl323（只读）
- **pymysql 已由 lib/db.py 内部处理，🚫 禁止 pip install**（沙箱 externally-managed，pip 必失败且白烧 3-5 个轮次）。
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
- 参考 `references/schema.md` — 完整表结构（来源: 实际 MySQL DDL）
- 参考 `references/business_rules.md` — 业务规则（来源: domains/evidens.txt）
- 参考 `references/few_shots.md` — SQL 示例（来源: domains/sqls.txt）
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）
- 参考 `shared/statistical_methods.md` — 统计分析方法（降雨量异常检测、移动平均、分布描述）
- 参考 `shared/sql_patterns.md` — SQL 通用查询模式（滚动累加、分组 Top-N）
- 参考 `shared/analysis_validation.md` — 分析验证（降雨统计的合理性检查）

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

- **⚡ 一轮完成"站点识别 + MAX(tm) 锚点 + 聚合主查询"：严禁拆成多个 LLM 回合。** 同一 Python 脚本内先 query() 拿真实 stcd/锚点（`SELECT MAX(tm) FROM st_pptn_r`），再 f-string 实值拼进主查询（同脚本代入安全；被禁止的是跨回合留 `{stcd}` 未填占位符）。"分步执行"指拆成多条简单 SQL，但都放在**同一脚本一轮跑完**。
- **⚡ 相对时间窗锚定 MAX(tm)，禁锚 CURDATE()/NOW()。** 库数据滞后于挂钟（实测停在 2026-06），锚 CURDATE() 的窗口常落空返 0 行。
- **⚡ 聚合优先。** 降雨"趋势/变化/分布"默认 `GROUP BY DATE(tm)` 日聚合 + SUM(drp)，禁拉原始行灌上下文。
- **⚠️ 模糊时间（"一段时间/近期"）默认近 30 天（锚 MAX(tm)）直接查，禁止向用户反问**——单轮评测反问=0 分。
- **⚠️ 分区裁剪：st_pptn_r/f_rnfl_h 是 RANGE 分区表**，禁 `YEAR(tm) IN (...)` 把 tm 包进函数，必须写 tm 连续区间；年度统计写 `tm >= '2024-01-01' AND tm < '2025-01-01'`（**不要** `BETWEEN '2024-01-01' AND '2024-12-31'`——datetime 上界丢掉整个 12-31）。

- **⚠️ 区域/站名列只在 `st_stbprp_b`，雨量表 `st_pptn_r` 只有 stcd+drp+tm。** 按区域聚合**必须 `JOIN st_stbprp_b b ON p.stcd=b.stcd`** 再 `GROUP BY b.addvcd`；禁止从 st_pptn_r 直接 SELECT addvcd（报 `Unknown column`）。也**禁止幻觉列 `addvnm`**（区域名称列不存在，只有 `addvcd` 码）。覆盖 Q30。
- **⚠️ 含单位/特殊字符的列别名必须加引号**（如 `AS '降雨量(mm)'`），**禁 CTE/`WITH`**（改子查询）。

## Workflow

1. **识别查询场景。** 实时降雨→st_pptn_r; 降雨预报→f_rnfl_h; 区域统计→st_pptn_r + GROUP BY addvcd。
2. **判断回复深度。** 根据用户问题的措辞和语境选择合适深度：
   - **精简模式**：用户问法简短（如"降雨量多少""最大""哪天"），没有"分析""趋势""详细""对比"等词
     - 优先从 `references/few_shots.md` 中匹配预设 SQL 并直接执行
     - 不要在 `dyp` 和 `drp` 之间犹豫——`few_shots.md` 中写什么字段就用什么字段
     - 不要做额外统计（平均、同比、趋势等）
     - 不要画图
     - 示例: "2024年扬州城区哪天降雨量最大" → 匹配 few_shot 示例直接执行
   - **标准模式**：用户问法包含"多少""情况""查一下"等中性词
     - 回答目标数据 + 1-2 个相关指标（如总量/均值/极值）
     - 不画图，不做趋势分析
   - **详细模式**：用户明确要求"分析""趋势""对比""详细""变化"等词
     - 可以做多维度统计分析（按月/季度聚合、同比/环比）
     - **画图仅当用户明确说"画图/图表/可视化"才触发**（与 water-situation 口径一致）；"分析/趋势/对比"默认文字结论+数据表，不画图
     - 画图时中文字体使用 `plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans']`
     - 可以做异常检测、趋势分析

   > **`drp` vs `dyp` 决策规则**：`dyp` 是日降水量但数据可能不全。优先用 `SUM(drp) GROUP BY DATE(tm)` 按天聚合。如果 `few_shots.md` 有对应的 SQL，直接使用不要怀疑。

3. **识别实体和时间。** 扬州城区固定 stcd='58245'。
4. **生成 SQL。** JOIN st_stbprp_b 获取测站/区域信息。
5. **预报场景。** f_rnfl_h JOIN f_rnfl_info_r，过滤 UNITNAME='2' AND TYPE='2'，取最新 FYMDH。降雨量字段是 **RN** 不是 f_rnfl。
6. **质量自检。** 执行 SQL 前确认符合安全规则。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。返回数值做合理性检查（日降雨量 0~500mm）。
7. **输出格式。** 根据判断的回复深度选择合适的输出格式：精简模式→只给出数值和日期；标准模式→给出查询范围+数值+简要说明；详细模式→完整上下文+分析。

## Validation Gate

**降雨量查询交付前必须通过以下检查。**

### 降雨量字段选择检查

- [ ] **优先用 drp 聚合**：`dyp` 是日降水量但数据可能不全，优先用 `SUM(drp) GROUP BY DATE(tm)` 按天聚合
- [ ] **预报场景字段正确**：f_rnfl_h 中是 **RN** 不是 f_rnfl

**常见错误示例**：
```sql
❌ 错误：SELECT dyp FROM st_pptn_r（dyp 可能为空）
✅ 正确：SELECT DATE(tm), SUM(drp) FROM st_pptn_r GROUP BY DATE(tm)
```

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl323.st_pptn_r | 降雨量 | stcd, tm(PK), drp(时段降水量), dyp(日降水量) |
| sl323.f_rnfl_h | 降雨预报 | ID(网格码), FYMDH(发布时间), YMDH(预报时间), **RN**(降雨量), UNITNAME, TYPE |
| sl323.f_rnfl_info_r | 网格信息 | id(网格码), adcd_name, adcd_code |
| sl323.st_stbprp_b | 测站信息 | sttp='PP' 为雨量站 |

## Business Rules Summary

- **扬州城区:** 固定 stcd='58245'
- **短临预报过滤:** UNITNAME='2'(扬州气象) AND TYPE='2'(短临)
- **降雨量字段:** f_rnfl_h 中是 **RN**，不是 f_rnfl
- **网格关联:** f_rnfl_h.ID = f_rnfl_info_r.id
- **drp vs dyp:** drp=时段降水量, dyp=日降水量

## Related Skills

- `water-situation` — 水位查询（降雨影响水位）
- `water-warning` — 防洪预警
- `water-visualization` — 降雨量柱状图、月度对比图
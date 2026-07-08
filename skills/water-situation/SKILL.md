---
name: water-situation
description: "水情综合查询 — 河道水位、水库水位、防洪指标、超警戒判断。核心表: sl323.st_river_r, sl323.st_rsvr_r, sl323.st_stbprp_b, sl323.st_rvfcch_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, river, reservoir, water-level, flood-control, hydrology, scada]
    category: water-resources
---

# 水情综合查询 (Water Situation)

查询河道/水库水位、防洪指标、超警戒判断。数据源: MySQL 192.168.100.103:3306/sl323。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询某河道实时/历史水位 | Yes |
| 查询水位是否超过警戒水位/保证水位 | Yes |
| 查询月度/年度水位统计（均值、最高、最低） | Yes |
| 查询重点河道水位（古运河、新城河、瘦西湖等） | Yes |
| 查询水库库水位、入库/出库流量、蓄水量 | Yes |
| 查询各站防洪指标（警戒水位、保证水位） | Yes |
| 水位趋势分析（涨/落/平） | Yes |
| 水位/流量异常检测（MAD/统计方法） | Yes — 参考 references/mad_anomaly_detection.md |
| 水量平衡检查（验证水位/流量一致性） | Yes — 参考 references/water_balance_check.md |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，数据库 sl323（只读）
- **连接:** pymysql, host='192.168.100.103', port=3306, user='root', password='<SL323_DB_PASSWORD>', database='sl323'
- **pymysql:** execute_code 环境可能未安装，首次使用需先运行 `pip install pymysql`
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**

## Pitfalls

- **`query()` 返回 `list[dict]`，不是 DataFrame。** 不能调用 `.iterrows()`, `.groupby()`, `.describe()` 等 pandas 方法。必须用 `for row in df: row['列名']` 或手动转 DataFrame: `import pandas as pd; df = pd.DataFrame(query(sql))`。
- **水库数据可能非常稀疏。** st_rsvr_r 表可能仅有最近1天的数据（如仅2025-05-19），远少于河道水情。查询前应先用 `SELECT MIN(tm), MAX(tm), COUNT(*) FROM st_rsvr_r WHERE rz IS NOT NULL` 确认实际数据范围，避免按"最近3个月"查出空结果。
- **站点编码格式不匹配。** 水库站（510B6180）、河道站（00000001）、闸门/泵站（HPBZCZ*）使用不同编码体系，无法直接 JOIN。跨域关联需先建立编码映射。
- **水库相关表大多为空。** st_rsvrfcch_b（库容曲线）、st_rsvrfcch_b（防洪参数）、st_rsvrav_r、st_rsvrevs_r（蒸发）在 2025-05 均为空表。水量平衡检查所需的历史流量（inq/otq）也全为空。做分析前应先确认哪些表有数据。
- **本库只含扬州地区站点。** sl323 库的行政区划码以 3210 开头（扬州）。如果用户查询的水库/站点在此库中找不到（如"三岔水库"），应提示用户该站点可能在调度数据库中，推荐切换到 `plan-generation` skill（连接本地 `powerelf_srm_yml` 库，包含调度预案和更多水库数据），而非反复在 sl323 中搜索。
- **无汛限水位字段。** st_rvfcch_b 仅有 WRZ（警戒水位）和 GRZ（保证水位），无"汛限水位"字段。水库防洪参数表 st_rsvrfcch_b 为空，因此系统中无法查询水库汛限水位。用户询问"距汛限水位多少米"时需说明该数据缺失。
- **数据库仅覆盖扬州地区。** st_stbprp_b 行政区划码以 3210xx 为主（扬州），不包含其他省市站点。用户询问非扬州地区的水库（如三岔水库、千岛湖等）时，应第一时间说明覆盖范围限制，避免无意义的多次模糊搜索。可用 `SELECT DISTINCT addvcd FROM st_stbprp_b` 快速确认覆盖区域。
- **db 模块路径:** `sys.path.insert(0, str(Path(__file__).parent / 'lib'))`。不要用其他路径。

## References

- 参考 `references/schema.md` — 完整表结构（来源: 实际 MySQL DDL）
- 参考 `references/business_rules.md` — 业务规则（来源: domains/evidens.txt）
- 参考 `references/few_shots.md` — SQL 示例（来源: domains/sqls.txt）
- 参考 `references/mad_anomaly_detection.md` — MAD 异常检测算法（水位突变/横向对比/变化速率）
- 参考 `references/water_balance_check.md` — 水量平衡检查方法（所需表、编码映射、替代方案）
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）
- 参考 `shared/statistical_methods.md` — 统计分析方法（水位百分位、趋势分析、异常检测）
- 参考 `shared/sql_patterns.md` — SQL 通用查询模式（窗口函数、移动平均、分组 Top-N）
- 参考 `shared/analysis_validation.md` — 分析验证（质量检查清单、常见陷阱、置信度评定）
- 参考 `shared/data_profiling.md` — 数据画像方法（探索新表时的系统化方法）

## Workflow

1. **识别查询场景。** 河道水位→st_river_r; 水库水位→st_rsvr_r; 防洪指标→st_rvfcch_b。
2. **识别测站/河道实体。** 参照重点河道映射（business_rules.md）。
3. **确定时间范围。** "实时/最新"→MAX(tm); "某天左右"→前后3天; "最近"→3天; "当前"→10天; "最近30天"→`tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)`; "最近2个月"→`INTERVAL 2 MONTH`。不要把窗口写窄(如把"最近30天"写成单天)。
4. **判断回复深度。** 根据用户问题的措辞和语境选择合适深度：
   - **精简模式**：用户问法简短（如"最高水位""多少""最低"），没有"分析""趋势""详细""对比"等词
     - 只查目标数据，不做额外分析
     - 不要画图，不要查警戒水位等扩展信息
     - 不要查比用户要求更细的时间粒度
     - 示例: "古运河过去一个月最高水位" → 只查 MAX(z) 并返回
   - **标准模式**：用户问法包含"多少""情况""查一下"等中性词
     - 回答目标数据 + 1-2 个相关指标（如最高/最低/平均）
     - 不画图，不做趋势分析
   - **详细模式**：用户明确要求"分析""趋势""对比""详细""变化""可视化""图"等词
     - 可以查多维度数据（均值、最高、最低、趋势、警戒）
     - 可以画图（matplotlib），但中文字体使用 `plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'DejaVu Sans']`，不要花时间寻找字体
     - 可以做异常检测、趋势分析等

   > ⚠️ **按站名直查,禁止占位符(高频错误)。** 当题目提到具体测站/河道名(宝应、白马闸、古运河…),**必须** `JOIN st_stbprp_b b ON r.stcd=b.stcd WHERE b.stnm LIKE '%站名%'` 按名直接查。**严禁**"先查 stcd 再用变量代入"的两步法——它会产生 `{stcd}`/`{dt}` 这类**未填值的占位符**,匹配 0 行。
   >
   > ❌ 错误(占位符污染,返回 0 行):
   > ```sql
   > SELECT z FROM st_river_r WHERE stcd='{stcd}' AND DATE(tm)='{dt}'
   > ```
   > ✅ 正确(按名 JOIN):
   > ```sql
   > SELECT r.tm, r.z FROM st_river_r r JOIN st_stbprp_b b ON r.stcd=b.stcd
   > WHERE b.stnm LIKE '%宝应%' AND r.tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
   > ```
   > 生成 SQL 后自检:**SQL 里不许出现 `{` `}` 占位符**;若有,立即改用 JOIN 按名查。

5. **生成 SQL。** JOIN st_stbprp_b 获取名称，LEFT JOIN st_rvfcch_b 获取警戒/保证水位。
6. **超警戒判断。** z > WRZ→超警戒; z > GRZ→超保证。
7. **水位保留两位小数。**
8. **质量自检。** 执行 SQL 前确认符合安全规则（只读、有 WHERE、有 LIMIT）。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。返回数值做合理性检查（水位 -1~20m）。
9. **统计增强（可选）。** 如需百分位分布、移动平均趋势、水位变率异常检测，参考 shared/statistical_methods.md。需窗口函数时参考 shared/sql_patterns.md。
10. **输出验证。** 交付前按 shared/analysis_validation.md 做置信度评定——特别是同比时注意不完整周期和均值之均值陷阱。

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl323.st_river_r | 河道水情 | stcd, tm(PK), z(水位), q(流量), wptn(水势) |
| sl323.st_rsvr_r | 水库水情 | stcd, tm(PK), rz(库水位), inq(入库), otq(出库), w(蓄水量), blrz(库下水位) |
| sl323.st_stbprp_b | 测站基础信息 | stcd, sttp(PK), stnm(名称), rvnm(河名) |
| sl323.st_rvfcch_b | 防洪指标 | STCD(无索引), WRZ(警戒), GRZ(保证), OBHTZ(实测最高) |

## Business Rules Summary

- **水势编码:** wptn 4=涨, 5=落, 6=平
- **测站类型:** ZZ=水位站, ZQ=水文站, RR=水库站
- **st_stbprp_b PK 是 (stcd, sttp)** 不是单独 stcd
- **st_rvfcch_b 无 PK**，STCD 上只有 INDEX
- **重点河道映射:** 详见 business_rules.md

## Related Skills

- `water-forecast` — 未来水位预测
- `water-warning` — 防洪预警判断
- `rainfall` — 降雨量查询（水位变化的关联因素）
- `water-visualization` — 水位趋势图、对比图
---
name: water-situation
description: "水情综合查询 — 河道水位、水库水位、防洪指标、超警戒判断。"
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
- **db 模块路径:** 使用 `lib/db.py` 助手模块，导入前需将 lib 目录加入 `sys.path`。不同平台的路径不同，详见 `shared/db_connection.md`。**推荐做法：根据部署平台选择对应的绝对路径**，避免使用 `Path(__file__)`（DeerFlow 执行环境中 `__file__` 不可靠）。
- **水体分类需前置标注（高频错误）。** `rvnm`（河名）字段将洪泽湖（湖泊）、长江（天然河流）、里运河（人工运河）同级归类，**不区分水体类型**。输出结果时需根据 `references/water_classification.md` 前置标注水体类型，避免语义混淆。参见 Validation Gate"水体分类一致性检查"。
- **高程基准不一致（高频错误）。** 本库存在多种高程基准：
  - 洪泽湖蒋坝站：`dtmnm='废黄河口'`，`dtmel=NULL`
  - 长江大通站：`dtmnm='冻结(吴淞)'`，`dtmel=-1.860`
  - **1985 国家高程基准在本库实测中未发现**
  - 跨站对比前必须确认基准相同，否则不能直接比绝对值。参见 Validation Gate"高程基准标注检查"。
- **阈值数据严重缺失（高频错误）。** `st_rvfcch_b` 表中：**GRZ（保证水位）全表 0% 有值**，**WRZ（警戒水位）水位站/水文站基本为空**（如蒋坝站 WRZ=NULL）。**绝对不要硬编码任何阈值**（如"洪泽湖警戒水位14.35m"无法在本库证实）。查询阈值前必须验证数据存在性，缺失时明确告知用户。参见 `references/threshold_query_validation.md` 和 Validation Gate"阈值数据存在性检查"。
- **单站代表性风险。** 本库洪泽湖、长江各仅 1 个测站（蒋坝、大通(二)），不存在"测站数量差异导致加权偏倚"的问题（等权均值=站均均值），但单站空间局限性需在报告中说明。参见 `references/single_station_representativeness.md` 和 Validation Gate"单站代表性检查"。

## References

- 参考 `references/schema.md` — 完整表结构（来源: 实际 MySQL DDL）
- 参考 `references/business_rules.md` — 业务规则（来源: domains/evidens.txt）
- 参考 `references/few_shots.md` — SQL 示例（来源: domains/sqls.txt）
- 参考 `references/mad_anomaly_detection.md` — MAD 异常检测算法（水位突变/横向对比/变化速率）
- 参考 `references/water_balance_check.md` — 水量平衡检查方法（所需表、编码映射、替代方案）
- 参考 `references/water_classification.md` — 水体分类知识库（湖泊/天然河流/人工运河的区分与报告规范）
- 参考 `references/elevation_datum.md` — 高程基准说明（废黄河口/吴淞分布、跨基准对比注意事项）
- 参考 `references/threshold_query_validation.md` — 阈值查询验证方法（查询前验证、缺失处理规范）
- 参考 `references/single_station_representativeness.md` — 单站代表性检查（单站结论评估框架）
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

5. **前置检查：水体分类与基准一致性。**
   - **水体分类**：若用户问题涉及"河流"、"河湖"、"水域"，查询前确认 `rvnm` 中是否包含湖泊/运河（如洪泽湖=湖泊，里运河=人工运河），参考 `references/water_classification.md`。输出结果时**前置标注水体类型**。
   - **高程基准**：若需跨站对比水位，联表 `st_stbprp_b` 查询两站 `dtmnm`（基准名称），若基准不同（如废黄河口 vs 冻结(吴淞)），需在报告中用 ⚠️ 标注"两站基准不同，绝对水位不可直比"。参考 `references/elevation_datum.md`。
   - **单站代表性**：若水域仅 1 个测站，需评估该站是否为控制站/代表站，并在报告末尾添加"数据局限性说明"。参考 `references/single_station_representativeness.md`。
6. **生成 SQL。** JOIN st_stbprp_b 获取名称，LEFT JOIN st_rvfcch_b 获取警戒/保证水位。
7. **阈值数据存在性验证（强制）。** 在查询 WRZ/GRZ 前，**必须**验证该测站阈值数据是否存在：
   ```sql
   SELECT COUNT(*) as cnt FROM st_rvfcch_b WHERE STCD='目标站码' AND (WRZ IS NOT NULL OR GRZ IS NOT NULL)
   ```
   若 cnt=0，**跳过阈值查询**，直接告知用户"⚠️ 该站阈值数据缺失"。详见 `references/threshold_query_validation.md`。
8. **超警戒判断（仅阈值存在时）。** z > WRZ→超警戒; z > GRZ→超保证。若 WRZ/GRZ 为 NULL，不判断超警状态。
9. **水位保留两位小数。**
10. **质量自检。** 执行 SQL 前确认符合安全规则（只读、有 WHERE、有 LIMIT）。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。返回数值做合理性检查（水位 -1~20m）。
11. **统计增强（可选）。** 如需百分位分布、移动平均趋势、水位变率异常检测，参考 shared/statistical_methods.md。需窗口函数时参考 shared/sql_patterns.md。
12. **输出验证。** 交付前按 Validation Gate 检查清单逐项验证，然后按 shared/analysis_validation.md 做置信度评定——特别是同比时注意不完整周期和均值之均值陷阱。

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

## Validation Gate

**每个水位分析交付前必须通过以下验证。** 未通过项标注在报告末尾。

### 水体分类一致性检查

- [ ] **分类前置标注**：若用户问题涉及"河流"、"河湖"、"水域"，输出结果中**必须标注水体类型**（湖泊/天然河流/人工运河/水库）
- [ ] **分类准确性**：使用 `references/water_classification.md` 中的映射表，确保分类正确
- [ ] **严格分类场景**：若用户要求"仅天然河流"，需过滤掉湖泊/人工运河

**示例**：
```markdown
❌ 错误：2024年平均水位最高的前3条河流依次为洪泽湖、长江、里运河
✅ 正确：2024年水域年均水位TOP3：洪泽湖（湖泊）13.148m、长江（天然河流）9.528m、里运河（人工运河）6.779m
```

### 高程基准标注检查

- [ ] **基准已标注**：报告中每个水位数值**必须标注基准来源**（`dtmnm` 字段值）
- [ ] **基准缺失说明**：若 `dtmnm` 为空或 `dtmel` 为 NULL，需说明"基准未记录"
- [ ] **跨站对比预警**：若对比的两个测站基准不同（如废黄河口 vs 吴淞），必须加注⚠️ 警告

**常见基准名称**（来自 `st_stbprp_b.dtmnm`）：
- `废黄河口`：里运河沿线（宝应、高邮等）
- `冻结(吴淞)`：长江大通站
- `1985 国家高程基准`：**本库实测中未发现任何测站使用此基准**

**示例**：
```markdown
洪泽湖年均水位 13.148m（基准：废黄河口）
长江年均水位 9.528m（基准：冻结(吴淞)）
⚠️ 两站基准不同，绝对水位横向比较仅供参考
```

### 阈值数据存在性检查

**⚠️ 重要警告**：`sl323.st_rvfcch_b` 表数据质量极差（GRZ 保证水位全表 0%，WRZ 警戒水位水位站基本为空）。

在查询任何阈值（WRZ/GRZ）之前，**必须**执行以下检查：

- [ ] **表中有数据**：`SELECT COUNT(*) FROM st_rvfcch_b WHERE STCD='xxx' AND (WRZ IS NOT NULL OR GRZ IS NOT NULL)`
- [ ] **字段值非空**：具体字段（WRZ/GRZ）不能为 NULL
- [ ] **数值合理性**：若阈值在 0~20m 范围之外，标记为异常

**阈值缺失时的处理**：
- ❌ **不要硬编码阈值**（如"洪泽湖警戒水位14.35m"无法在本库证实）
- ❌ **不要猜测或估算**
- ✅ **必须告知用户**："⚠️ 该站阈值数据缺失，无法判断超警戒状态"
- ✅ **提供替代方案**：可提供历史极值作为参考（明确标注"非官方阈值"）

**查询验证示例**（详见 `references/threshold_query_validation.md`）：
```python
def validate_threshold(stcd: str) -> dict:
    # Step 1: 验证表中有数据
    cnt = query(f"SELECT COUNT(*) as cnt FROM st_rvfcch_b WHERE STCD='{stcd}' AND (WRZ IS NOT NULL OR GRZ IS NOT NULL)")
    if cnt[0]['cnt'] == 0:
        return {'valid': False, 'message': f'⚠️ {stcd} 阈值数据全部缺失'}

    # Step 2: 验证字段值
    row = query(f"SELECT WRZ, GRZ FROM st_rvfcch_b WHERE STCD='{stcd}'")[0]
    if row['WRZ'] is None:
        warn('⚠️ 警戒水位数据缺失（WRZ=NULL）')
    # ...
```

### 单站代表性检查

针对涉及**水位均值统计**的场景，评估单站代表性：

- [ ] **测站数量统计**：查询该水域测站数量 `COUNT(DISTINCT stcd)`
- [ ] **代表性评估**：
  - ≥5 站：✅ 多站均值，代表性较高
  - 2~4 站：⚡ 代表性中等
  - 1 站：⚠️ 单站，需进一步评估
- [ ] **单站情况额外检查**：
  - 是否为控制站/代表站（查询 `business_rules.md` 重点测站映射）
  - 是否位于流域关键位置（入湖/出湖口、干支流交汇处）
  - 数据质量（缺测率、异常值比例）
- [ ] **报告末尾添加"数据局限性说明"**

**示例**：
```markdown
洪泽湖 2024 年年均水位 13.148m（蒋坝站，位于入湖口，为控制站，单站代表性较高）

⚠️ **局限性**：本库洪泽湖仅蒋坝 1 站，若需全湖均值建议补充湖心、出湖口等测站。
```

### 统计口径说明

- [ ] **均值计算口径已说明**：等权算术平均 / 加权平均 / 站均的均值
- [ ] **权重差异说明**：若水域存在多测站，需说明是否按数据量加权或等权
- [ ] **实测验证**：对于关键结果，建议实测"等权均值 vs 站均均值"差值（本库实测差值 = 0.000）

**示例**：
```markdown
统计口径：里运河 4 站水位数据直接算术平均（等权）
验证：全量等权平均 = 站均均值 = 6.779m（差值 0.000），无加权偏倚
```

### 数值合理性检查（继承 shared/analysis_validation.md）

- [ ] **水位范围**：-1 ~ 20m（超出需标记异常）
- [ ] **数据完整性**：缺测率 < 阈值（如 5%）
- [ ] **时间序列连续性**：无意外断点
- [ ] **边界情况**：空集合/零值/缺失段时查询是否正常运行？

### 置信度评定

通过以上所有检查 → **高置信度**（可直接交付）

存在以下情况 → **有保留**（报告中标注具体问题）：
- 1~2 项水体分类/基准/阈值检查未通过
- 单站代表性受限但结论仍可用

存在以下情况 → **需修订**（返回 Workflow 修正）：
- 3+ 项检查未通过
- 基准未标注且跨站对比
- 阈值硬编码且无法证实
- 单站代表性极差（如偏僻小站代表大流域）
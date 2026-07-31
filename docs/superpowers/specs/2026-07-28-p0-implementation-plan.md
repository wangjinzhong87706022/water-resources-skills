# P0 落地方案详述

> **日期**：2026-07-28
> **范围**：P0-1 表知识卡片化 + P0-2 eval 错误归因
> **预估工作量**：3-4 天（表卡片化 2-3 天 + eval 归因 1 天）

---

## P0-1: 表知识卡片化（S3/S5/S6）

### 目标

在现有 `schema.md`（纯 DDL）基础上，为每个核心表补充 **业务语境**，让 LLM 选表时能看到"此表适用什么场景、口径怎么算、常见坑在哪"。直接消灭已知高频错误：占位符污染、分区超时、阈值硬编码。

### 现状分析

| 维度 | 现状 | 问题 |
|------|------|------|
| 表总数 | **18 张**（6 skill × 3 表） | — |
| `schema.md` 内容 | 字段/类型/含义（DDL 级） | 无业务场景、无口径、无模板 |
| 业务知识位置 | 散落在 `SKILL.md` Pitfalls、`business_rules.md`、`few_shots.md` | LLM 选表时看不到，必须翻多份文档 |
| 高频错误根因 | 占位符污染、分区超时、阈值硬编码 | 均因"口径未附着到表"导致 |

**典型场景**（当前workflow）：

```
用户问："古运河最近30天水位趋势"
  ↓
LLM 看到 schema.md: st_river_r 有 z(水位)、tm(时间)字段
  ↓
不知道：
  - S3: st_river_r 适用=河道实时/历史水位（✅），但不适用=水库（❌应用 st_rsvr_r）
  - S5: tm 必须用连续区间（❌禁用 YEAR(tm) IN 否则分区超时）
  - S6: 按站名查询必须 JOIN st_stbprp_b（❌不能两步法查 stcd 再代入）
  ↓
生成错误 SQL → 分区超时 / 返回 0 行 / 占位符污染
```

### 改造方案

在每个 `skills/<skill>/references/schema.md` 的**每个表节**后，追加三节：

#### S3 场景映射（Scene Mapping）

```markdown
### S3 场景映射 — st_river_r

| 适用场景 | 不适用场景 | 典型查询模式 |
|---------|-----------|-------------|
| 查询河道实时/历史水位 | 查询水库水位（用 st_rsvr_r） | `SELECT z FROM st_river_r WHERE stcd = ? AND tm >= ?` |
| 水位趋势分析（涨/落/平） | 跨年对比（必须带 tm 连续区间） | `SELECT tm, z FROM ... WHERE tm >= '2023-01-01' AND tm < '2025-01-01'` |
| 月度/年度水位统计 | 水质查询（用 sl325 库） | `SELECT AVG(z), MAX(z), MIN(z) FROM ... GROUP BY YEAR(tm)` |
| 超警戒判断（联表 st_rvfcch_b） | 降雨量查询（用 st_rain_r） | `JOIN st_rvfcch_b ON stcd = STCD WHERE z > WRZ` |

**关联表**：st_stbprp_b（测站名称）、st_rvfcch_b（警戒/保证水位）
```

#### S5 口径定义（Caliber Definition）

```markdown
### S5 口径定义 — st_river_r

**字段业务口径**：

| 字段 | 业务含义 | 范围/约束 | 特殊规则 |
|------|---------|----------|---------|
| stcd | 测站编码 | char(18)，与 st_stbprp_b.stcd 一致 | **必须 JOIN st_stbprp_b 按 stnm 查，禁止先查 stcd 再代入**（占位符污染高频坑） |
| tm | 观测时间 | datetime，PK | **RANGE(tm) 分区表，WHERE 必须用连续区间**：`tm >= '2023-01-01' AND tm < '2025-01-01'`。禁止 `YEAR(tm) IN (2023,2024)`（分区裁剪失效，实测 434s 超时） |
| z | 水位 | decimal(38,3) | 范围 **-1 ~ 20m**，超出需标记异常 |
| q | 流量 | decimal(38,3) | 单位 m³/s，部分测站无流量数据（q IS NULL） |
| wptn | 水势编码 | char(1) | **4=涨, 5=落, 6=平**（编码需前置说明） |

**分区规则**：
- 分区键：`tm`（RANGE 分区，p2023~p2026）
- 裁剪条件：`WHERE tm >= 'YYYY-MM-DD' AND tm < 'YYYY-MM-DD'`
- 反模式：`YEAR(tm) = 2024`、`MONTH(tm) = 8`、`DATE(tm) BETWEEN ...`

**编码映射**：
- 河道站 stcd 格式：`3210XXXX`（扬州地区）
- 水库站 stcd 格式：`510BXXXX`（不同编码体系，无法直接 JOIN）
```

#### S6 SQL 模板（SQL Skeleton）

```markdown
### S6 SQL 模板 — st_river_r

**模板 1：按站名查水位（高频，占位符防护）**

```sql
SELECT r.tm AS '时间', r.z AS '水位(m)', r.q AS '流量(m³/s)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%{站名}%'  -- 直接按名查，禁止两步法
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL {天数} DAY)
  AND r.z IS NOT NULL
ORDER BY r.tm;
```

**模板 2：月度/年度统计（分区裁剪合规）**

```sql
SELECT
  YEAR(tm) AS '年份',
  AVG(z) AS '平均水位(m)',
  MAX(z) AS '最高水位(m)',
  MIN(z) AS '最低水位(m)'
FROM sl323.st_river_r
WHERE tm >= '{起始日期}' AND tm < '{结束日期}'  -- 必须连续区间
  AND stcd IN ('{stcd1}', '{stcd2}')  -- 提前查好 stcd
GROUP BY YEAR(tm)
ORDER BY YEAR(tm);
```

**模板 3：超警戒判断（联表阈值）**

```sql
SELECT b.stnm AS '测站名称',
       MAX(r.z) AS '最高水位(m)',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN MAX(r.z) > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
LEFT JOIN sl323.st_rvfcch_b rv ON b.stcd = rv.STCD
WHERE b.stnm LIKE '%{站名}%'
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL {天数} DAY)
  AND rv.WRZ IS NOT NULL  -- 阈值存在性检查前置
GROUP BY b.stnm, rv.WRZ;
```
```

### 实施步骤

#### Phase 1: 提取口径信息（0.5 天）

从现有文档提取 S3/S5/S6 素材：

| 素材来源 | 提取内容 | 工具 |
|---------|---------|------|
| `SKILL.md` Pitfalls | 分区坑、占位符、高程基准、阈值缺失 | grep/手动 |
| `business_rules.md` | 水体分类、重点河道映射、水势编码 | 直接引用 |
| `few_shots.md` | 高频 SQL 模式 | grep "SELECT" / "JOIN" |
| `shared/sql_patterns.md` | 窗口函数、移动平均、分组 Top-N | 直接引用 |

**输出**：`scripts/extract_caliber.py` 脚本（一次性使用），生成各表素材草稿。

#### Phase 2: 批量写入 S3/S5/S6（1.5 天）

按 skill 逐个处理（6 个 skill，每 skill ~30 分钟）：

```bash
# 顺序处理
skills=(water-situation rainfall water-quality water-forecast gate-pump-operation water-warning)

for skill in "${skills[@]}"; do
  echo "Processing $skill..."
  # 1. 读取现有 schema.md
  # 2. 对每个表节追加 S3/S5/S6
  # 3. 写入 schema.md
done
```

**质量门控**：
- [ ] 每个表都有 S3/S5/S6 三节
- [ ] 分区表（st_river_r/st_was_r/st_pump_r/st_pump_pa）S5 明确列出分区规则和反模式
- [ ] 阈值相关表（st_rvfcch_b）S5 明确"GRZ 全表 0% 有值，WRZ 水位站基本为空"
- [ ] SQL 模板已验证可执行

#### Phase 3: 验证与更新引用（0.5 天）

1. **更新 SKILL.md References 节**：在 `references/schema.md` 后增加
   ```markdown
   - 参考 `references/schema.md` §S3/S5/S6 — 表业务场景/口径/SQL 模板
   ```

2. **更新 Key Tables 节**：为每个表增加"场景映射"列
   ```markdown
   | sl323.st_river_r | 河道水情 | stcd, tm(PK), z(水位) | ✅水位趋势 | ❌水库水位 |
   ```

3. **回归测试**：运行 `evaluate_skills.py --skill water-situation --level L1` 验证未破坏现有功能

### 验收标准

| 检查项 | 通过条件 |
|--------|---------|
| **完整性** | 18 张表全部有 S3/S5/S6 |
| **分区表覆盖** | 4 张分区表（st_river_r/st_was_r/st_pump_r/st_pump_pa）S5 明确列出反模式 |
| **阈值表覆盖** | st_rvfcch_b S5 明确 GRZ/WRZ 数据质量（0% 有值/基本为空） |
| **SQL 模板可执行** | 每个模板的示例参数在数据库实测通过 |
| **Eval 不退化** | eval 总分下降 < 2%（仅文档补充，不应影响 SQL 生成） |

### 基线数据（2026-07-28 全量 98 题）

**全量基线**（来源：`docs/superpowers/specs/2026-07-28-deerflow-baseline-98.md`）：

| Skill | 题数 | 平均分 | 通过率 | SQL率 |
|-------|------|--------|--------|-------|
| gate-pump-operation | 15 | 0.79 | 100.0% | 40.0% |
| rainfall | 18 | 0.73 | 94.4% | 94.4% |
| water-forecast | 13 | 0.76 | 76.9% | 76.9% |
| water-quality | 13 | 0.78 | 92.3% | 61.5% |
| water-situation | 25 | 0.68 | 88.0% | 84.0% |
| water-warning | 14 | 0.80 | 92.9% | 64.3% |
| **总体** | **98** | **0.75** | **90.8%** | **72.4%** |

**低分用例（9 题，待 P0 修复）**：
- Q2 [water-situation/L1]：宝应站字段查询不完整（0.38 分）
- Q15 [water-situation/L3]：白马闸实时水位（0.53 分）
- Q19 [water-situation/L3]：2025 年古运河水位站数量（0.58 分）
- Q26 [rainfall/L1]：扬州城区今日降雨量（0.55 分）
- Q56 [water-quality/L3]：水质站所属河流（0.43 分）
- Q58 [water-forecast/L1]：最新预测任务状态（0.43 分）
- Q66 [water-forecast/L3]：历史预测任务完成次数（0.50 分）
- Q69 [water-forecast/L3]：今天预测任务状态（0.55 分）
- Q88 [water-warning/L2]：水质低于Ⅳ类站点（0.50 分）

**P0 目标**：
- 平均分从 0.75 → ≥ 0.775（+3%）
- 低分用例从 9 题 → ≤ 4 题（-50%+）

---

## P0-2: eval 错误归因

### 目标

在现有 `evaluate_skills.py` 评分体系基础上，增加**失败用例归因标签**，让迭代从"准确率 80%"升级为"30% 错在选表 → 优先修路由表"。

### 现状分析

当前评分维度（5 个）：

| 维度 | 权重 | 问题 |
|------|------|------|
| has_valid_response | 20% | 只看是否非空，不区分错误类型 |
| has_domain_data | 30% | 关键词命中数，无法定位错误环节 |
| has_numeric_data | 25% | 有数字不代表正确 |
| response_quality（SQL 相似度） | 25% | 相似度低不知道是选表错/SQL 语法错/语义错 |
| sql_safe | 0%（仅检查） | 无归因能力 |

**缺失能力**：
- ❌ 失败用例无"错在哪一环"分类
- ❌ 无法统计"30% 错在选表 → 优先修路由"
- ❌ 无法追踪迭代效果（"修了路由后选表错误从 30% 降到 10%"）

### 归因维度设计

基于水利 skill 典型错误模式，定义 **5 类归因标签**：

| 归因标签 | 检测规则 | 典型场景 |
|---------|---------|---------|
| **选表错** (table_selection) | LLM 选的表与 expected_sql 主表不一致 | 问水位却查 st_rsvr_r（水库表） |
| **SQL 语法错** (sql_syntax) | actual_sql 无法解析或执行失败 | 占位符污染（`{stcd}`）、缺少 JOIN ON、LIMIT 缺失 |
| **口径错** (caliber) | 表选对了但字段/条件/分区规则错误 | `YEAR(tm) IN` 导致分区超时、z 单位用错、阈值硬编码 |
| **语义模糊** (ambiguity) | 问题本身歧义或缺少澄清 | "古运河水位"未说明是实时/历史/统计 |
| **其他错误** (other) | 无法归类 | 超时、连接失败、API 错误 |

### 改造方案

#### 1. 新增 `ErrorAttributor` 类

```python
# skills/scripts/evaluate_skills.py

class ErrorAttributor:
    """错误归因器"""

    @staticmethod
    def attribute(case: TestCase, actual_sql: str, response: str, scores: dict) -> dict:
        """
        对失败用例归因

        Returns:
            {
              "label": str,  # table_selection/sql_syntax/caliber/ambiguity/other
              "confidence": float,  # 0~1，归因置信度
              "detail": str,  # 详细说明
              "fix_hint": str  # 修复建议
            }
        """
        # 规则 1: SQL 完全未生成 → sql_syntax 或 other
        if not actual_sql:
            if scores.get("has_valid_response", 0) < 0.5:
                return {
                    "label": "other",
                    "confidence": 0.8,
                    "detail": "响应为空或报错",
                    "fix_hint": "检查 hermes 执行日志"
                }
            # 有响应但无 SQL → 可能是语义模糊或 LLM 未输出代码块
            return {
                "label": "sql_syntax",
                "confidence": 0.6,
                "detail": "有响应但未提取到 SQL",
                "fix_hint": "检查 SQL 是否在代码块内"
            }

        # 规则 2: 选表不一致（主表名对比）
        expected_tables = ErrorAttributor._extract_tables(case.expected_sql)
        actual_tables = ErrorAttributor._extract_tables(actual_sql)
        if expected_tables and actual_tables:
            overlap = expected_tables & actual_tables
            if not overlap:
                return {
                    "label": "table_selection",
                    "confidence": 0.9,
                    "detail": f"期望表: {expected_tables}, 实际表: {actual_tables}",
                    "fix_hint": "检查 skill 路由表或关键词映射"
                }

        # 规则 3: 分区规则违反（口径错典型）
        if ErrorAttributor._has_partition_violation(actual_sql):
            return {
                "label": "caliber",
                "confidence": 0.85,
                "detail": "分区表 WHERE 条件违反分区裁剪规则（使用 YEAR/MONTH 函数）",
                "fix_hint": "改为 tm 连续区间: tm >= '2023-01-01' AND tm < '2025-01-01'"
            }

        # 规则 4: 占位符污染（SQL 语法错典型）
        if ErrorAttributor._has_placeholder(actual_sql):
            return {
                "label": "sql_syntax",
                "confidence": 0.95,
                "detail": "SQL 含未填值占位符（如 {stcd}、{dt}）",
                "fix_hint": "改为 JOIN st_stbprp_b 按 stnm 直查"
            }

        # 规则 5: 阈值硬编码（口径错典型）
        if ErrorAttributor._has_hardcoded_threshold(actual_sql, response):
            return {
                "label": "caliber",
                "confidence": 0.8,
                "detail": "硬编码阈值（如 '14.35m'）",
                "fix_hint": "先查询 st_rvfcch_b 验证阈值存在性"
            }

        # 规则 6: 语义模糊（问题本身多义）
        if ErrorAttributor._is_ambiguous_question(case.question):
            return {
                "label": "ambiguity",
                "confidence": 0.7,
                "detail": "问题歧义，缺少时间范围/统计口径",
                "fix_hint": "增加澄清步骤"
            }

        # 规则 7: SQL 执行失败（语法/逻辑错误）
        if scores.get("sql_safe", {}).get("safe") is False:
            issues = scores["sql_safe"].get("issues", [])
            return {
                "label": "sql_syntax",
                "confidence": 0.75,
                "detail": f"SQL 安全检查失败: {', '.join(issues)}",
                "fix_hint": "检查 SQL 语法规则"
            }

        # 兜底：低分但无法精确归因
        if scores.get("total_score", 1.0) < 0.4:
            return {
                "label": "other",
                "confidence": 0.5,
                "detail": "总分低但无法精确定位错误类型",
                "fix_hint": "人工检查 trajectory"
            }

        return {"label": "other", "confidence": 0.3, "detail": "未识别到错误", "fix_hint": ""}

    @staticmethod
    def _extract_tables(sql: str) -> set[str]:
        """提取 SQL 中的表名（简化版）"""
        import re
        tables = set()
        # 匹配 FROM/JOIN 后的表名
        matches = re.findall(r'(?:FROM|JOIN)\s+([\w.]+)', sql, re.IGNORECASE)
        for m in matches:
            # 去掉库名前缀，保留表名
            table = m.split('.')[-1].strip('`').strip('"')
            if table:
                tables.add(table)
        return tables

    @staticmethod
    def _has_partition_violation(sql: str) -> bool:
        """检测是否违反分区裁剪规则"""
        import re
        # 检查是否在 WHERE 条件中对分区键 tm 使用函数
        return bool(re.search(
            r'\b(YEAR|MONTH|DAY|DATE)\s*\(\s*tm\s*\)',
            sql,
            re.IGNORECASE
        ))

    @staticmethod
    def _has_placeholder(sql: str) -> bool:
        """检测占位符污染"""
        import re
        return bool(re.search(r'\{[\w_]+\}', sql))

    @staticmethod
    def _has_hardcoded_threshold(sql: str, response: str) -> bool:
        """检测阈值硬编码（简单版：数字+单位+m）"""
        import re
        combined = sql + response
        # 匹配 13.5m、14.35m 等水位数字
        return bool(re.search(r'\b\d+\.\d{2}\s*m\b', combined, re.IGNORECASE))

    @staticmethod
    def _is_ambiguous_question(question: str) -> bool:
        """检测问题是否缺少关键信息"""
        # 缺少时间范围词
        time_words = ['最近', '过去', '历史', '实时', '当前', '某天', 'month', 'day']
        has_time = any(w in question for w in time_words)
        # 缺少统计口径词
        stat_words = ['平均', '最高', '最低', '最大', '最小', '统计']
        has_stat = any(w in question for w in stat_words)
        return not has_time or not has_stat
```

#### 2. 集成到 `evaluate_single()` 函数

在 `evaluate_single()` 函数末尾（`return result` 前），调用归因器：

```python
# ---- 错误归因（仅失败用例） ----
if result.total_score < 0.6:  # 失败阈值
    attribution = ErrorAttributor.attribute(
        case, result.actual_sql, result.actual_response, result.scores
    )
    result.scores["attribution"] = attribution
else:
    result.scores["attribution"] = {"label": "pass", "confidence": 1.0, "detail": "通过"}
```

#### 3. 报告增加"错误归因"章节

修改 `generate_report()` 函数，在 Markdown 报告中增加：

```markdown
## 错误归因分析

### 归因分布

| 错误类型 | 数量 | 占比 | 典型示例 |
|---------|------|------|---------|
| 选表错 (table_selection) | 12 | 30% | Q7 水位趋势误选 st_rsvr_r |
| SQL 语法错 (sql_syntax) | 8 | 20% | Q15 占位符污染、Q23 缺少 JOIN ON |
| 口径错 (caliber) | 15 | 37.5% | Q5 分区超时、Q19 阈值硬编码 |
| 语义模糊 (ambiguity) | 3 | 7.5% | Q33 缺少时间范围 |
| 其他 (other) | 2 | 5% | Q41 超时 |

### 高频错误 Top 3（迭代优先级）

1. **口径错 37.5%** → 优先完善 S5 口径定义（特别是分区规则）
2. **选表错 30%** → 优化关键词映射表（planner.py SKILL_TABLES）
3. **SQL 语法错 20%** → 增强 SQL 安全检查和代码块提取

### 按 Skill 归因热力图

| Skill | table_selection | sql_syntax | caliber | ambiguity |
|-------|----------------|------------|---------|-----------|
| water-situation | 5 | 3 | 8 | 1 |
| rainfall | 2 | 2 | 3 | 1 |
| ... | ... | ... | ... | ... |
```

### 实施步骤

#### Phase 1: ErrorAttributor 实现（0.5 天）

1. 创建 `ErrorAttributor` 类（含 6 条规则 + 兜底）
2. 单元测试：准备 10 个典型失败用例验证归因准确性
3. 集成到 `evaluate_single()` 函数

#### Phase 2: 报告增强（0.3 天）

1. 修改 `generate_report()` 增加"错误归因分析"章节
2. JSON 报告增加 `attribution_summary` 字段

#### Phase 3: 验证与基线（0.2 天）

1. 全量跑一次 eval（98 题）生成归因基线
2. 人工抽查 20% 失败用例验证归因准确性
3. 输出 `docs/eval/eval_attribution_baseline_20260728.md`

### 验收标准

| 检查项 | 通过条件 |
|--------|---------|
| **归因覆盖率** | 失败用例（total_score < 0.6）归因标签覆盖率 100% |
| **归因准确率** | 人工抽查 20% 失败用例，准确率 ≥ 80% |
| **报告完整性** | Markdown 报告包含归因分布、Top 3 错误、按 Skill 热力图 |
| **性能影响** | eval 总耗时增加 < 10%（归因逻辑为 O(n) 字符串匹配） |
| **可追踪性** | 每个失败用例的归因结果写入 JSON 报告（含 detail + fix_hint） |

### 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| **归因规则误判** | 中 | 部分用例分类错误 | 初期设 `confidence` 字段，低置信度（< 0.7）标为 `other` 待人工确认 |
| **阈值硬编码检测误伤** | 低 | 正常水位数值被误判 | 规则加入上下文（检查是否出现在 SQL WHERE 条件 vs 报告文本） |
| **分区规则检测不全** | 低 | 新型反模式漏检 | 定期从 trajectory 反哺新规则（如 `BETWEEN` 嵌套函数） |

---

## 实施时间线

| 日期 | P0-1 表卡片化 | P0-2 eval 归因 |
|------|-------------|--------------|
| **Day 1** | Phase 1: 提取口径信息（脚本开发） | Phase 1: ErrorAttributor 实现 + 单元测试 |
| **Day 2** | Phase 2: 批量写入 S3/S5/S6（water-situation + rainfall） | Phase 2: 报告增强 |
| **Day 3** | Phase 2: 批量写入（剩余 4 个 skill） | Phase 3: 基线生成 + 人工验证 |
| **Day 4** | Phase 3: 回归测试 + 验收 | **完成** |

**并行策略**：Day 2 可两人并行（一人做表卡片化，一人做 eval 归因 Phase 2），Day 3 合并验证。

---

## 成功指标

| 指标 | 基线（2026-07-28） | P0 完成后目标 |
|------|-------------------|-------------|
| eval 总分 | [需跑一次基线] | 提升 ≥ 3%（消除高频坑） |
| 选表错误率 | [需归因基线] | 降低 ≥ 20%（修路由表） |
| 分区超时失败率 | [需归因基线] | 降低 ≥ 50%（S5 口径补全） |
| 占位符污染失败率 | [需归因基线] | 降低 ≥ 80%（S6 模板防护） |
| 错误归因覆盖率 | 0% | 100%（失败用例有标签） |

---

## 后续衔接

- **P1 路由表收敛**：归因基线数据将明确"选表错"占比，若 > 25% 则 P1 优先级提升至 P0
- **Ablation 实验**：P0 完成后可作为 ablation 基线（对比"无表卡片化 + 无 eval 归因"的性能）

---

## 附录 A: 全量 98 题基线数据（2026-07-28）

**来源**：`docs/superpowers/specs/2026-07-28-deerflow-baseline-98.md`

### A.1 总体评分

| 指标 | 值 |
|------|-----|
| 平均分 | 0.75 |
| 通过率（≥0.6） | 90.8%（89/98） |
| SQL 提取率 | 72.4%（71/98） |
| 总耗时 | 27.1 分钟 |
| 平均耗时 | 16.6 秒/题 |

### A.2 按 Skill 汇总

| Skill | 题数 | 平均分 | 通过率 | SQL率 | 平均耗时 |
|-------|------|--------|--------|-------|----------|
| gate-pump-operation | 15 | 0.79 | 100.0% | 40.0% | 14.9s |
| rainfall | 18 | 0.73 | 94.4% | 94.4% | 5.8s |
| water-forecast | 13 | 0.76 | 76.9% | 76.9% | 20.0s |
| water-quality | 13 | 0.78 | 92.3% | 61.5% | 33.9s |
| water-situation | 25 | 0.68 | 88.0% | 84.0% | 9.4s |
| water-warning | 14 | 0.80 | 92.9% | 64.3% | 26.0s |

### A.3 按难度汇总

| 难度 | 题数 | 平均分 | 通过率 |
|------|------|--------|--------|
| L1 | 15 | 0.69 | 80.0% |
| L2 | 21 | 0.77 | 95.2% |
| L3 | 62 | 0.75 | 91.9% |

### A.4 低分用例（9 题，< 0.6 分）

| 题号 | Skill/难度 | 问题 | 得分 | SQL |
|------|-----------|------|------|-----|
| Q2 | water-situation/L1 | 查询宝应水位站的所属河流、水系、流域、测站类别。 | 0.38 | ✓ |
| Q15 | water-situation/L3 | 查询水位站白马闸的实时水位是多少。 | 0.53 | ✓ |
| Q19 | water-situation/L3 | 查询2025年古运河水位站点的数量。 | 0.58 | ✓ |
| Q26 | rainfall/L1 | 查询扬州城区今日降雨量。 | 0.55 | ✓ |
| Q56 | water-quality/L3 | 查询有哪些水质站？分别属于哪条河流？ | 0.43 | ✓ |
| Q58 | water-forecast/L1 | 查询最新预测任务的状态。 | 0.43 | ✓ |
| Q66 | water-forecast/L3 | 查询历史上有多少次预测任务已完成。 | 0.50 | ✓ |
| Q69 | water-forecast/L3 | 查询今天有哪些预测任务，分别是什么状态？ | 0.55 | ✓ |
| Q88 | water-warning/L2 | 查询水质低于Ⅳ类的站点。 | 0.50 | ✓ |

### A.5 P0 改造目标

| 指标 | 基线 | P0 目标 |
|------|------|---------|
| 平均分 | 0.75 | ≥ 0.775（+3%） |
| 低分用例数 | 9 题 | ≤ 4 题（-50%+） |
| 通过率 | 90.8% | ≥ 93%（+2%） |

---

## 附录 B: P0 实施时间线

| 日期 | P0-1 表卡片化 | P0-2 eval 归因 |
|------|-------------|--------------|
| **Day 1** | Phase 1: 提取口径信息（脚本开发） | Phase 1: ErrorAttributor 实现 + 单元测试 |
| **Day 2** | Phase 2: 批量写入 S3/S5/S6（water-situation + rainfall） | Phase 2: 报告增强 |
| **Day 3** | Phase 2: 批量写入（剩余 4 个 skill） | Phase 3: 基线生成 + 人工验证 |
| **Day 4** | Phase 3: 回归测试 + 验收 | **完成** |

**并行策略**：Day 2 可两人并行（一人做表卡片化，一人做 eval 归因 Phase 2），Day 3 合并验证。

---

**文档版本**：v1.0（2026-07-28）
**下次更新**：P0 改造完成后更新基线数据和验收结果

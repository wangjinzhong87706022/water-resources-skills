# 高德 NL2SQL 实践对照分析与评测改进行动方案

> **日期**：2026-07-30
> **来源文章**：《NL2SQL 在超大规模数仓场景的架构突破与工程实践》（高德 · 薛飞跃，https://mp.weixin.qq.com/s/RDIMNWfITiBqC7e8pBa8bw）
> **定位**：当前处于评测迭代阶段，本文档以「评测相关改进」为主线（A1/A2 为 P0），架构类改进（A3/A4）为后续衔接。
> **关联文档**：`2026-07-28-nl2sql-feasibility-analysis.md`（可行性分析）、`2026-07-28-p0-implementation-plan.md`（P0-2 ErrorAttributor 原始设计）、`2026-07-28-eval-strategy.md`

---

## 1. 文章核心要点速览

高德场景：9 业务域、352 张 ODPS 表、~30,000 行知识库，NL2SQL 准确率 >95%。

| # | 高德实践 | 一句话 |
|---|---------|--------|
| 1 | V1→V2 演进 | 分域 9 Skill → 统一 Skill + 四层架构（L1 域路由 / L2 按需知识加载 / L3 统一 6 步工作流 / L4 公共层），根因是「路由决策在控制范围之外」 |
| 2 | 确定性路由 > RAG | 业务术语语义重叠使 embedding 不可靠；域可枚举 → 规则穷举，可调试可追溯 |
| 3 | 6 节知识卡片 | S1 元数据 / S2 字段 / S3 场景映射 / S4 关联方式 / S5 口径定义 / S6 SQL 模板 |
| 4 | 口径澄清机制 | 歧义时不问开放问题，只给 2-3 个候选选项 |
| 5 | 评测驱动 + 错误归因 | 900+ 题回归；错题四分类：选表错 / SQL 语法错 / 口径错 / 语义模糊 → 定向修复 |
| 6 | AI-Friendly 标准分 | 字段覆盖率 / 口径完整度 / SQL 模板覆盖率 / 场景标注率 / 路由规则完备度，量化知识质量 |
| 7 | DDL 一致性监控 | 定期 diff 线上表结构 vs 知识库文档，防「沉默失败」 |
| 8 | 用户反馈闭环 | 三类沉默信号（纠正 / 重复提问不一致 / 放弃对话）→ 问题池 → 周度 review |

核心结论：**NL2SQL 的天花板在知识质量，不在模型能力**。

---

## 2. 与本仓库对照矩阵

### 2.1 已对齐（无需动作）

| 高德实践 | 本仓库现状 | 证据 |
|---------|-----------|------|
| 6 节知识卡片 | S3/S5/S6 卡片已落地（P0-1 成果） | `skills/water-situation/references/schema.md`（710 行，按表分节含 S3/S5/S6） |
| L4 公共服务层 | `skills/shared/` 1,762 行单份共享 | sql_safety_rules / sql_patterns / common_schema 等 |
| 评测驱动迭代 | 98 题 + 回归门禁 + 消融实验 | `skills/docs/test-cases-with-sql.md`、`skills/scripts/run_gate.py`、`ablation_fusion.py` |
| SQL 自检 + 质量基线 | 12 步 Workflow + Validation Gate 三档置信度 | `skills/water-situation/SKILL.md:130-320` |

### 2.2 合理拒绝（维持现状，已有决策记录）

| 高德实践 | 拒绝理由 | 决策出处 |
|---------|---------|---------|
| 渐进式知识加载 | 全仓知识 ~5,000 行 vs 高德 30,000 行，现代上下文窗口可容纳 | feasibility 分析 §0 |
| DDL 监控 / 元数据 Pipeline | 18 张表且 schema 稳定，手工维护成本更低；已有一次性验证脚本 `verify_knowledge.py` | feasibility 分析 §5 |
| 合并为单一超大 Skill | 水利域边界比高德清晰，多 skill + fusion 编排更贴合平台形态 | feasibility 分析 §0 |

### 2.3 差距（本方案的行动项）

| 编号 | 差距 | 高德对应实践 | 优先级 | 阶段 |
|------|------|-------------|--------|------|
| A1 | 评测错误归因仅 infra/sql_error/other 三类技术分类，无业务归因 | 错题四分类驱动定向修复 | **P0** | 评测（当前） |
| A2 | 全仓无口径澄清机制（grep "澄清" 零命中），评测也不考核澄清行为 | 歧义时给 2-3 个候选选项 | **P0** | 评测 + Skill |
| A3 | 路由知识分散（fusion 关键词表 6 行 + `planner.py`），单域路由靠平台黑盒 | L1 确定性域路由表 + 消歧规则 | P1 | 架构 |
| A4 | 知识质量无量化评分 | AI-Friendly 标准分 | P2 | 工具 |
| A5 | 无用户反馈闭环 | 沉默信号检测 + 问题池 | 观望 | 运营 |

---

## 3. A1（P0）：错误归因五分类落地到当前评测通道

### 3.1 目标

失败用例（total_score < 0.6）100% 带归因标签，评测报告输出归因分布与迭代优先级建议，实现「30% 错在选表 → 优先修路由映射」的定向迭代。

### 3.2 现状与差距

- `skills/scripts/verifiers.py:127` `_classify_failure` 只有 `infra / sql_error / other` 三类，且只作用于单条 execute_code 调用，目的为剔除 infra 噪音，**不是业务归因**。
- `2026-07-28-p0-implementation-plan.md:224+` 已有完整 `ErrorAttributor` 设计（5 类标签 + 6 条规则），但原设计目标文件是 `evaluate_skills.py`（hermes 通道）；**当前评测主通道是 `evaluate_deerflow.py`**（分支 `fix/eval-deerflow-sql-execution`），需要调整落点。

### 3.3 归因标签（沿用 P0-2 设计）

| 标签 | 检测规则 | 典型场景 |
|------|---------|---------|
| `table_selection` 选表错 | actual_sql 主表集合与 expected_sql 主表集合无交集 | 问河道水位却查 st_rsvr_r |
| `sql_syntax` SQL 语法错 | SQL 无法执行 / 含占位符 `{stcd}` / 未提取到 SQL | 占位符污染、缺 JOIN ON |
| `caliber` 口径错 | 表选对但字段/分区/条件错 | `YEAR(tm)` 破坏分区裁剪、阈值硬编码 |
| `ambiguity` 语义模糊 | 问题歧义且系统未澄清 | "古运河水位"未指明实时/历史 |
| `other` 其他 | infra、超时、API 错误 | 连接失败 |

### 3.4 实施步骤

**落点决策：新建 `skills/scripts/error_attributor.py` 独立模块**（而非塞进某个 evaluate_*.py），理由：当前有 4 条评测通道（evaluate_skills / evaluate_deerflow / \_e2e / \_gateway），独立模块可被全部通道复用。

#### Step 1：实现 `error_attributor.py`（~150 行，0.5 天）

```python
# skills/scripts/error_attributor.py
"""失败用例业务归因。与 verifiers._classify_failure（技术分类，用于剔除
infra 噪音）互补：本模块回答「错在取数链路的哪一环」。"""
import re
from dataclasses import dataclass

LABELS = ("table_selection", "sql_syntax", "caliber", "ambiguity", "other")

# 复用 verifiers.py 的 infra 判定，infra 一律归 other（非 agent 错）
from verifiers import _classify_failure  # noqa

_TABLE_PAT = re.compile(r"(?:FROM|JOIN)\s+([a-zA-Z_][\w.]*)", re.I)
_PLACEHOLDER_PAT = re.compile(r"\{[a-z_]+\}")
_PARTITION_VIOLATION_PAT = re.compile(r"(?:YEAR|MONTH|DATE_FORMAT)\s*\(\s*tm\s*\)", re.I)

def extract_main_tables(sql: str) -> set:
    return {t.lower().split(".")[-1] for t in _TABLE_PAT.findall(sql or "")}

@dataclass
class Attribution:
    label: str
    confidence: float
    detail: str
    fix_hint: str

def attribute(question: str, expected_sql: str, actual_sql: str,
              response: str, exec_error: str = "") -> Attribution:
    # 规则顺序 = 置信度排序，先命中先返回（详见 p0-implementation-plan.md 规则 1-6）
    ...
```

规则实现直接照抄 `2026-07-28-p0-implementation-plan.md` 的规则 1-6（含 `_has_partition_violation` / `_has_placeholder` / `_has_hardcoded_threshold` / `_is_ambiguous_question`），此处不重复。

**与 `verifiers._classify_failure` 的分工**：exec_error 先过 `_classify_failure`，返回 `infra` 的直接归 `other`（`detail="infra failure, 非 agent 错"`），避免重蹈 HALO 诊断发现的「infra 当 agent 失败」污染问题。

#### Step 2：集成到 `evaluate_deerflow.py`（0.2 天）

在 `run_eval()`（`evaluate_deerflow.py:417`）中 `score_case` 调用之后（约 line 464 后）：

```python
from error_attributor import attribute

if total_score < 0.6:
    attr = attribute(case["question"], case["expected_sql"],
                     actual_sql, response, exec_error=exec_err)
    scores["attribution"] = vars(attr)
else:
    scores["attribution"] = {"label": "pass"}
```

同样方式集成到 `evaluate_skills.py`（在 `evaluate_single()` 末尾）——两个通道共用同一模块。

#### Step 3：报告增强 `generate_report()`（`evaluate_deerflow.py:356`，0.3 天）

Markdown 报告新增章节（格式沿用 p0-implementation-plan 的设计）：

```markdown
## 错误归因分析
| 错误类型 | 数量 | 占比 | 失败题号 |
|---------|------|------|---------|
| caliber | 4 | 44% | Q5, Q19, Q41, Q77 |
| table_selection | 3 | 33% | Q7, Q23, Q52 |
| ...

### 迭代优先级建议（自动生成）
1. caliber 44% → 优先补 S5 口径定义（涉及表：st_river_r, st_rvfcch_b）
2. table_selection 33% → 检查 SKILL.md Key Tables / S3 场景映射
```

JSON 报告增加 `attribution_summary: {label: count}` 顶层字段。

#### Step 4：单元测试 + 归因基线（0.3 天）

1. `skills/scripts/test_error_attributor.py`：从 `skills/reports/` 已有低分用例中取 10 个真实样本（如 baseline-98 报告中的 9 题低分用例），断言归因标签符合人工判断。
2. 全量跑一轮 98 题（用当前分支通道），产出**归因基线报告**存 `skills/reports/`，人工抽查 10 个归因标签准确率 ≥ 80%。
3. 归因分布写回本文档 §6 验收表。

### 3.5 验收标准

- [ ] 失败用例归因覆盖率 100%
- [ ] 人工抽查归因准确率 ≥ 80%（10 例抽样）
- [ ] evaluate_deerflow 与 evaluate_skills 两通道报告均含归因章节
- [ ] run_gate 回归通过（归因是只读附加，不得影响原评分）

---

## 4. A2（P0）：口径澄清机制 + 澄清类评测用例

### 4.1 目标

Skill 在遇到歧义问题时主动给出 2-3 个候选选项而非猜测；评测能够考核「该澄清时是否澄清了」。这直接消化 A1 中 `ambiguity` 类失分。

### 4.2 水利场景的歧义清单（先枚举再写规则）

| 歧义术语 | 候选口径 | 归属 skill |
|---------|---------|-----------|
| "水位" | A. 河道站水位（st_river_r.z） B. 水库站水位（st_rsvr_r.rz） | water-situation |
| "雨量" | A. 时段雨量（drp） B. 日累计 C. 场次累计 | rainfall |
| "最近/近期" | A. 最新一条 B. 近 24h C. 近 7 天 | 全部 |
| "XX河水位"（河道有多站） | A. 代表站 B. 全部站点 C. 沿程分布 | water-situation |
| "超警" | A. 超警戒（wrz） B. 超保证（grz） | water-warning |
| "闸门状态" | A. 开度（gtopw） B. 过闸流量（tgtq） C. 启闭状态 | gate-pump-operation |

> 落地前由数据同学补全/修订此表，作为唯一权威歧义清单，存入 `skills/shared/ambiguity_rules.md`。

### 4.3 Skill 侧改造（每个 data skill 约 +10 行）

在各 SKILL.md Workflow 的「识别查询场景」步骤之前插入统一规则（文案全仓一致，来自 shared）：

```markdown
### Step 0.5 · 歧义检查（必须）
对照 shared/ambiguity_rules.md 检查问题是否命中歧义术语且上下文无法消歧。
命中时**不要猜测**，输出候选选项让用户选择，格式：
> 您问的"水位"是指：A. 河道站水位  B. 水库站水位？
规则：① 只给 2-3 个选项，不问开放问题；② 上下文已可消歧（如"XX水库水位"）则直接继续；
③ 用户已选择过的口径在会话内沿用，不重复问。
```

**消歧优先于澄清**：如问题含"水库"则直接判 B 不发问——澄清是消歧规则穷尽后的兜底，避免过度打断（高德原则同）。

### 4.4 评测侧改造

#### Step 1：测试集新增 `clarify` 题型（~10 题）

`skills/docs/test-cases-with-sql.md` 新增分节，题目字段扩展：

```markdown
### C1 [L2-clarify] 古运河最近水位怎么样？
- expected_behavior: clarify
- expected_options_contains: ["河道", "代表站|全部站"]
- followup: "看代表站"
- expected_sql_after_followup: SELECT ...
```

选题来源：§4.2 歧义清单逐行至少 1 题 + baseline 报告中歧义导致的真实低分题。

#### Step 2：评分逻辑（`evaluate_deerflow.py` / `verifiers.py`）

`clarify` 题型两阶段评分：

| 阶段 | 检查 | 分值 |
|------|------|------|
| 阶段 1 | 响应是否为澄清（含 2-3 个候选选项、无 SQL 执行、无编造数值） | 0.4 |
| 阶段 2 | 注入 followup 后生成的 SQL 与 expected_sql_after_followup 比对（沿用现有 sql_similarity + result_correctness） | 0.6 |

反向约束：**非 clarify 题若发起澄清则扣分**（`-0.2`），防止 skill 学会「见问题就反问」刷分。

#### Step 3：回归验证

1. 先只改评测（Step 1-2），跑一轮确认现状：预期 clarify 题阶段 1 全部 0 分（现状无澄清能力）→ 形成澄清基线。
2. 再落地 §4.3 Skill 改造，跑 run_gate：clarify 题阶段 1 得分 ≥ 0.8 × 题数，且原 98 题总分不回退（重点盯住是否出现过度澄清扣分）。

### 4.5 验收标准

- [ ] `skills/shared/ambiguity_rules.md` 建立且经数据同学 review
- [ ] 6 个 data skill SKILL.md 均含 Step 0.5（文案一致）
- [ ] clarify 题型 ≥ 10 题入库，评分逻辑落地
- [ ] 澄清命中率 ≥ 80%，原 98 题总分无回退（±1% 内）
- [ ] A1 归因报告中 `ambiguity` 占比对比改造前下降 ≥ 50%

---

## 5. A3（P1）/ A4（P2）：架构与工具类改进（评测阶段后启动）

### A3：统一 L1 确定性路由表

- **问题**：路由知识分散在 `water-fusion/SKILL.md:145-154`（6 行关键词表）与 `lib/planner.py`（SKILL_TABLES + BUSINESS_DEPENDENCIES）两处；单域路由依赖 hermes/DeerFlow 平台黑盒——正是高德 V1 的问题二「路由在控制范围之外，无法调试」。
- **方案**：新建 `skills/shared/routing_table.md` 作为唯一权威路由表，格式对齐高德「典型指标关注点 + 判断要点 + 易混淆消歧规则」：

  ```markdown
  | 意图特征 | 目标 skill | 消歧规则 |
  |---------|-----------|---------|
  | 水位/河道/水库/超警戒判断 | water-situation | 含"预测/未来"→ water-forecast |
  | 降雨/雨量/预报 | rainfall | 含"雨情+水情联合"→ water-fusion |
  | ...
  ```

  `water-fusion/SKILL.md` 与 `planner.py` 均改为引用该表（planner 可由 CI 脚本从 md 表生成常量,保证单一来源）。
- **验收**：路由决策可回答「为什么选了这个 skill」；A1 归因中 `table_selection` 类错误下降 ≥ 20%。
- **前置依赖**：A1 归因基线（先量化选表错占比，再决定投入力度）。

### A4：轻量 AI-Friendly 标准分脚本

- **方案**：`skills/scripts/check_knowledge_quality.py`（~100 行），按 skill 输出四项得分：
  1. **字段覆盖率**：DDL 字段（可从 `verify_knowledge.py` 的连库能力取 DESC）是否都出现在 schema.md;
  2. **S3 场景标注率**：schema.md 中每个表分节是否含「适用/不适用」;
  3. **S5 口径完整率**：核心指标是否有计算口径（正则检 S5 节非空）;
  4. **S6 模板覆盖率**：每表是否有 ≥1 个参数化 SQL 模板。
- 输出 Markdown 评分表,接入 `run_gate.py` 作为非阻断告警项。
- **价值**：A1 归因发现某 skill `caliber` 错误集中时,标准分直接定位是哪张表的 S5 缺失。

### A5：用户反馈闭环（观望）

有真实用户流量后再启动。届时优先实现高德三类沉默信号中成本最低的一类：**同一问题多次提问但结果不一致**（可完全从日志离线检测,无需用户配合）。

---

## 6. 实施顺序与总验收

```
A1 ErrorAttributor（1.3 天）──→ 归因基线报告
        │                          │
        ▼                          ▼
A2 澄清机制+clarify 题（2 天）   A3 路由表收敛（视归因数据决定,~1 天）
        │
        ▼
A4 标准分脚本（0.5 天,可并行）
```

| 指标 | 当前基线 | 目标 |
|------|---------|------|
| 失败用例归因覆盖率 | 0% | 100% |
| 归因标签人工抽查准确率 | — | ≥ 80% |
| clarify 题澄清命中率 | 0%（无能力） | ≥ 80% |
| ambiguity 类失分占比 | 待 A1 基线 | 下降 ≥ 50% |
| table_selection 类失分占比 | 待 A1 基线 | 下降 ≥ 20%（A3 后） |
| 98 题总分 | 0.75（2026-07-28 基线） | 不回退,随定向修复稳步提升 |

---

## 7. 风险与注意事项

1. **归因规则是启发式**，置信度字段必须保留并在报告中展示；低置信度（<0.7）的归因在人工 review 时优先复核。
2. **澄清与流畅性的平衡**：过度澄清比不澄清更伤体验。反向扣分规则（§4.4 Step 2）必须与正向规则同时上线。
3. **评分兼容性**：A1/A2 均为评测附加项，不得改动 `score_case` 现有权重与 floor-lift 逻辑,否则历史基线不可比。若 clarify 题型需要独立评分路径,新增题型分支而非修改主路径。
4. **LLM 随机性**：P0-1 报告已记录 7 题波动。归因分布对比需跑 ≥2 轮取并集/均值,避免把随机波动当成迭代效果。

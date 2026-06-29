# SQL 质量审查流程

> 所有水利 skill 通用。流程:**Step 1-2(生成自检)→ 独立对抗审查(仅高风险查询,执行前最后闸门)→ 执行 SQL → Step 3(空结果重试)→ Step 4(合理性检查)**。
>
> 关键原则:高风险查询不能只靠"自检"。必须委派一个**独立 reviewer sub-agent**(`delegate_task`,隔离上下文)做对抗审查。self-certify(自己查自己)是已知失效模式,会放过"看着合理实则错答"的静默失败(详见 Anthropic 数据分析实践 + Hermes Eval Harness)。

## Step 1: 表名列名校验

- 检查 SQL 中的表名是否在当前 skill 的 `references/schema.md` 中定义
- 检查列名是否在 schema.md 的列清单中（防止拼写错误）
- 特别注意大小写敏感的列名：
  - `st_rvfcch_b.STCD`（大写）vs `st_river_r.stcd`（小写）
  - `st_mx_preset_cal_r.type` 是 varchar，`st_mx_preset_r_shj_auto.type` 是 int

## Step 2: 时间条件完整性

- 所有查询**必须包含时间范围条件**
- "最新/当前/实时" → 取 MAX(tm) 或 ORDER BY tm DESC LIMIT 1
- "最近N天" → `tm >= DATE_SUB(CURDATE(), INTERVAL N DAY)`
- "某天左右" → 前后 3 天范围
- "本月/当月" → `tm >= DATE_FORMAT(CURDATE(), '%Y-%m-01')`
- 预测表：先查最新任务时间，若距今过久需告知用户

## 独立对抗审查（高风险查询 · 执行前最后闸门）

> Step 1-2 是主 agent 自检（零成本，先挡低级错误）。本节针对**高风险查询**追加一个**独立 reviewer sub-agent**——它不看本对话历史，只审 SQL 本身，专挑会导致错答或超时的真问题。
>
> **低风险查询**（单表 + 简单时间过滤，如 `rainfall` 查扬州城区 `stcd='58245'` 今日降雨）**跳过本节**，直接执行 SQL。

### 何时触发（满足任一即为高风险）

- **跨库查询**：同时涉及 sl323 与 sl325/slztk
- **分区表**：`st_was_r` / `st_pump_r` / `st_pump_pa`（按 tm RANGE 分区，无时间条件会全分区扫描超时）
- **超警戒/超保证判断**：JOIN `st_rvfcch_b`（STCD 大小写易错）
- **闸泵综合汇总**：多表（st_gate_r + st_was_r + st_pump_r）合并
- **水质 6 级评级**：CASE WHEN 单因子评价

### 用 `delegate_task` 调起独立 reviewer

reviewer 必须**隔离上下文**（不继承本对话）。调用范式（参照 `skills/software-development/requesting-code-review` 的 fail-closed reviewer 模板）：

```
delegate_task(
  goal=<见下方 reviewer goal>,
  context=<待审 SQL + 涉及表的 schema 片段（取自 references/schema.md）+ 本 skill 的 gotchas（取自 references/business_rules.md）>,
  role="leaf"
)
```

**reviewer goal（直接套用，强制 JSON 输出）**：

> 你是独立的 SQL 对抗审查员。你没有任何本对话上下文，只依据下面给出的 SQL、表结构和已知陷阱做判断。目标是找出会导致**错误结果**或**超时**的真问题，不是挑风格毛病。
>
> **FAIL-CLOSED 规则**（任一命中 → `passed` 必须为 false）：
> - SQL 无 WHERE 子句
> - 查询分区表（st_was_r / st_pump_r / st_pump_pa）但 WHERE 中无 `tm` 时间条件
> - 字段大小写/类型错：`st_rvfcch_b` 用了小写 `stcd`；`st_mx_preset_cal_r.type` 用数字而非引号；水质监测表用了 `tm` 而非 `spt`
> - 明显 SQL 注入风险或语法错误
> - 无法解析 SQL → `passed` 为 false
>
> 只返回 JSON，不要任何额外文字：
> ```
> {"passed": true|false, "findings": [{"severity":"RED|YELLOW", "category":"...", "issue":"...", "fix":"..."}], "notes":"..."}
> ```
> `passed=true` 当且仅当无 RED finding。

**异常处理**（照搬 requesting-code-review 的 fail-closed）：reviewer 返回非 JSON → 用更严格的 prompt **重试一次** → 仍失败则按 **FAIL** 处理（不执行该 SQL，向用户说明审查未通过，不能自我放行）。

### Pragmatism filter（主 agent 对 findings 分级，过滤噪音）

拿到 reviewer 的 findings 后，主 agent 做四级分类（参照 `optional-skills/dogfood/adversarial-ux-test` 的对抗+过滤分离范式）：

| 级别 | 含义 | 处理 |
|------|------|------|
| **RED** | 真 blocking（命中上方 FAIL-CLOSED 规则） | **必须修复**，修复后**重新 delegate 审查**，passed 才执行 |
| **YELLOW** | 可优化但不阻断（缺 LIMIT、JOIN 可简化） | 记录，放行执行 |
| **WHITE** | 风格噪音（缩进、别名风格） | 丢弃 |
| **GREEN** | 发现的 schema/业务规则改进点（新歧义字段等） | 记录为 SKILL.md/reference patch 候选（反哺文档） |

- **配额**：RED 最多上报 **5** 条，聚焦最严重，防 reviewer 刷量。
- **放行条件**：仅当 RED 全部修复且重审 `passed=true`，才执行 SQL。YELLOW 不阻断执行。

## Step 3: 空结果处理

如果执行结果为空，按以下策略**自动重试一次**：

1. **扩大时间范围** — 如 "最近3天" → "最近10天"
2. **模糊匹配名称** — 如 `= '古运河'` → `LIKE '%古运河%'`
3. **检查河流别名** — 参照各 skill 的 `business_rules.md` 中的重点河道映射
4. **检查测站类型** — 确认 sttp 过滤条件是否正确

## Step 4: 结果合理性检查

返回结果前，快速验证数值合理性：

| 数据类型 | 合理范围 | 异常处理 |
|---------|---------|---------|
| 水位 (z/rz) | -1 ~ 20 m | 超出范围提示单位可能有误 |
| 降雨量 (drp/dyp) | 0 ~ 500 mm | 单日 > 200mm 需标注"极端降雨" |
| 流量 (q) | 0 ~ 10000 m³/s | 负值提示数据异常 |
| 水质 CODMn | 0 ~ 50 mg/L | > 30 需标注"严重超标" |
| 水质 DO | 0 ~ 20 mg/L | < 2 需标注"缺氧" |
| 水位保留两位小数 | ROUND(z, 2) | 所有水位输出必须保留2位 |

## 输出溯源 footer（所有查询结果必须附带）

返回查询结果时，末尾附带 provenance footer（模板与字段见 `shared/provenance_footer.md`），至少包含：**来源表**、**数据新鲜度**（`MAX(tm)` 及距今）、**skill 版本**、**审查状态**（是否经独立对抗审查）。

这是防"静默失败（答案错但看着合理）被直接转发"的最后防线——用户/下游看到 footer 能判断该不该信这个结果。数据陈旧（> 3 天）或预测非实时必须在 footer 中高亮提示。

> 完整的可观测（trajectory 回放 / APMPlus）见 `shared/observability.md`（runtime/配置层，对接任务 #1）。

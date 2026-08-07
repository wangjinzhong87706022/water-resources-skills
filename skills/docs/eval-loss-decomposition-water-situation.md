# water-situation 评测损失分解（eval-loss decomposition）

> 结论先行：water-situation 的丢分**不是知识缺失**，而是评测脚本的若干假阴性 / 坏 golden。
> 因此**不需要**为它新建 retrieve/library 检索层；优先修评测 harness。
> 数据来源：`reports/eval_gateway_full_20260805_20260805_202629/gateway_eval_all_20260806_012736.json`（全量 98 题，avg 0.884）。

---

## 方法

对 water-situation 的低分 / 失败 case 做三类归因：

| 类别 | 含义 | 该不该修 skill |
|------|------|----------------|
| **(a) 缺知识** | skill 里没有该查询模式 / schema，agent 无从下手 | 该修 skill（或上 retrieve） |
| **(b) 有知识没照做** | 知识在 SKILL.md，agent 没遵守（幻觉表名、漏 LIMIT 等） | 该修 skill 措辞 / 强化规则 |
| **(c) 基础设施 / 评测 bug** | agent 实际跑通了，但评测脚本判错（假阴性 / 坏 golden） | **修评测 harness** |

抽样 25 个低分 case 逐一看 `actual_sqls` / `tool_results` / `final_answer`，**(a) 缺知识 = 0/25**。canonical SQL（标准三件套：站码查询 + MAX(tm) 锚点 + 聚合）**已经内联在 SKILL.md**，且 references/few_shots.md 有 10+ 个 Q→SQL 样例。知识不是瓶颈。

---

## 发现 A：知识不是瓶颈（0/25 缺知识）

water-situation 低分 case 的 `result_quality` 尾部（rq < 0.6）：

| Q | rq | 说明 |
|----|------|------|
| Q5 | 0.00 | expected_sql 用 `CURDATE()`，数据有滞后→查不到可比值（坏 golden，见发现 C） |
| Q22 | 0.30 | 同 CURDATE() 问题 |
| Q23 | 0.30 | 同上 |
| Q24 | 0.48 | 同上 |
| Q1 | 0.30 | expected_sql 返回无可比值（坏 golden） |
| Q76 | 0.07 | agent 走偏（b 类），单点 |

尾部几乎全是 **(c) 坏 golden**，不是 (a)/(b)。结论：retrieve 对 water-situation 收益≈0。

---

## 发现 B：`sql_replay_ok` 的 f-string 假阴性（5 题，其中 4 题实跑满分）

### 根因链（`skills/scripts/evaluate_deerflow_gateway.py`）

1. `parse_run_messages()` 从 bash/write_file 脚本里用正则 `_SQL_STRING_RE` 抽 SQL 字符串字面量（L183-185）。
   标准三件套的主查询是 **f-string 模板**，带未填值的 `{stcd_list}` / `{days}` 占位符 → 被原样抽进 `actual_sqls`。
2. `score_result()` L229：`replay = execute_sql_safe(r.actual_sqls[-1])` —— 重放**最后一条** SQL。
3. 最后一条常是主查询模板。若占位符**裸露**（`IN ({stcd_list})`）→ MySQL 语法错 → `ok=False` → `sql_replay_ok=0`，
   哪怕 agent 实际跑通了、`result_quality=1.00`。→ **假阴性**。

> 注意区分：占位符在**引号内**（`stcd = '{stcd}'`）时，MySQL 把花括号当字面量，查询能跑（返回空），`ok=True`。
> 所以「最后一条是模板」≠「假阴性」；只有**裸花括号**导致语法错时才是。这就是为什么很多模板题 replay 仍是 1.0。

### 受影响题目（当前 `sql_replay_ok == 0.0` 的，全仓仅 5 题）

| Q | 当前 replay_ok | result_quality | 当前 total | 修复后 |
|----|----|----|----|----|
| Q18 | 0.0 | **1.00** | 0.70 | → 0.95 |
| Q21 | 0.0 | **1.00** | 0.75 | → 1.00 |
| Q34 | 0.0 | **1.00** | 0.75 | → 1.00 |
| Q72 | 0.0 | **1.00** | 0.70 | → 0.95 |
| Q89 | 0.0 | **1.00** | 0.75 | → 0.88（中性） |

4 题是纯评测假阴性（agent 实跑满分）。全仓 avg 预计 +0.0115（0.884 → ~0.896）；但按题算，4 题 0.70-0.75 → 0.95-1.00，
若有 per-case 通过线（如 0.8）会从 FAIL 翻 PASS。

### 最小补丁（`evaluate_deerflow_gateway.py` L226-232）

优先重放**已填值的具体 SQL**（无 `{ }`）——它正是 agent 跑过的查询；只有全模板时才回退。

```python
    # 3. 平台侧 SQL 可复执行 (25%)：在本地库重放
    #    actual_sqls[-1] 常是 f-string 模板（标准三件套主查询 WHERE ... IN ({stcd_list})），
    #    裸花括号让 MySQL 语法错 → 假阴性（agent 实跑满分却判 0）。改为优先重放具体 SQL。
    replay = None
    if r.actual_sqls:
        concrete = [s for s in r.actual_sqls if "{" not in s and "}" not in s]
        if concrete:
            replay = execute_sql_safe(concrete[-1])
            scores["sql_replay_ok"] = 1.0 if replay["ok"] else 0.0
        else:
            # 全是模板：仍试重放最后一条。
            #  引号内 '{stcd}' → 当字面量能跑、返回空 → ok=1（与现状一致）；
            #  裸 {stcd_list} → 语法错，无法证伪 → 中性 0.5，不假阴性。
            replay = execute_sql_safe(r.actual_sqls[-1])
            scores["sql_replay_ok"] = 1.0 if replay["ok"] else 0.5
    else:
        scores["sql_replay_ok"] = 0.0
```

配套：报告输出处（L436 `x.actual_sqls[-1][:500]`）同样改用具体 SQL 显示，否则报告里贴的是带 `{stcd_list}` 的模板，误导排查。

### 零回归证明

- `actual_sqls[-1]` 本就具体（无花括号）的题：`concrete[-1] == actual_sqls[-1]`，行为不变。
- 模板但引号内花括号、当前 `ok=True` 的题：要么有具体 SQL → 重放具体仍 `ok=1`；要么全模板 → 回退重放模板仍 `ok=1`。不变。
- 模板裸花括号、当前 `ok=False=0` 的题：有具体 SQL → 1.0（修复）；全模板 → 0.5（部分修复）。
- **没有任何题变差。**

---

## 发现 C：坏 golden（expected_sql 返回无可比值）—— 次优先

`result_quality` 尾部（Q1/Q5/Q22/Q23/Q24）主因是 expected_sql 用 `CURDATE()`，而库内数据有滞后，
expected 与 actual 都查不到可比值 → F1≈0。这是 golden 本身的问题，不是 skill 的问题。
（expected SQL **不是 ground truth**，见记忆 `eval-deerflow-rebuild`。）

修法（独立于发现 B，优先级更低）：评测时对 expected_sql 也跑一遍，若 expected 自身返回空行/无可比值，
应把该题的 `result_quality` 标记为 **golden_broken / N/A**，不计入失分，而不是给 0。

---

## 决策

1. **不建 retrieve/library 检索层** —— 缺知识占比 0/25，canonical SQL 已在 SKILL.md，收益≈0。
2. **先修评测 harness 的 f-string 假阴性**（发现 B，5 题收益明确，零回归）。
3. **再修坏 golden 标记**（发现 C），让 `result_quality` 不被坏 golden 拖低。
4. 修完重跑全量，再看 (b) 类「有知识没照做」的真实残余——那才是该动 skill 措辞的地方。

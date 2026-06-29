# HALO 式跨 case 诊断报告 — water-resources harness baseline

> **方法**:HALO 思路(发现级聚合 → 手术级精读 → 只读诊断,数据观察非指令)。
> 对 corrected 基线 `reports/harness_baseline/eval_results_20260623_175514_corrected.json`(98 题)做跨 case 诊断。
> **性质:trace evidence,不是修复指令。命名文件/约束缺失处,需独立验证后再行动。**
> 日期 2026-06-25。

## TL;DR

**当前基线(avg 0.783 / pass 92.9%)严重失真,失真源是测量管道,不是 agent。**
三个系统性信号:

1. **`sql_correctness` 82/98 skip** —— verifier 因 `(1040, 'Too many connections')` 连不上共享 MySQL,无法判定 SQL 正确性。
2. **`sql_executes` 62/98 fail + `tool_trace_sanity` 81/98 fail** —— 同一批 MySQL 1040 连接失败被两个 verifier 当作"agent 工具失败"重复计分,压低了 sql_execution 和 trace 两层。
3. **`actual_sql` 字段大半为空** —— 真 SQL 在 `messages/*.json` 的 `execute_code` tool_call 里(eval_results 的 `actual_sql` 不可靠,只读它会被误导)。

**结论:在 DB 1040 饱和状态下采的基线不可用于 regression gate。** 必须先解决测量管道,再谈 skill 改进。

---

## 发现级:跨 case 聚合(发现级,无单条全文)

### 信号 A — Verifier 子项失败密度

| verifier 子项 | fail(<1.0) | skip(<0) | total | 性质 |
|---|---|---|---|---|
| `tool_trace_sanity` | **81** | 0 | 98 | 受 DB 1040 污染(见信号 C) |
| `sql_executes` | **62** | 0 | 98 | 受 DB 1040 污染 |
| `domain_coverage` | 21 | 0 | 98 | 真实信号(答案缺领域关键词) |
| `sql_correctness` | 12 | **82** | 98 | 82 skip 全是 1040 连不上 |
| `numeric_presence` | 1 | 0 | 98 | 健康 |
| `response_validity` | 1 | 0 | 98 | 健康 |
| `sql_safety` | 0 | 0 | 98 | 健康(危险操作一票否决正常) |

`tool_trace_sanity` 83% / `sql_executes` 63% 失败,但 `sql_safety` 0 失败、`final_answer` 三项近乎全过 —— 失败**高度集中在"需要连 DB 才能判定"的层**。这是测量管道问题的指纹:若是 agent 能力问题,失败会均匀分布;若是管道问题,失败集中在依赖外部(DB)的层。

### 信号 B — 按 skill 分布(纠正 memory 记录)

| skill | n | avg | sql_exec fail | tool_trace fail |
|---|---|---|---|---|
| water-forecast | 13 | **0.721** | 11 | 13 |
| rainfall | 18 | 0.798 | 14 | 18 |
| water-quality | 13 | 0.831 | 7 | 9 |
| water-warning | 14 | 0.830 | 10 | 10 |
| water-situation | 25 | 0.815 | 18 | 19 |
| gate-pump-operation | 15 | 0.838 | 8 | 12 |

**纠正 memory**:旧记录"36 mismatch 全在 water-situation,根因占位符污染"不成立。
- `sql_executes`/`tool_trace_sanity` 失败**跨全部 skill**,非 water-situation 独有。
- 最差是 **water-forecast(0.721/pass 77%)**,不是 water-situation(0.815/pass 96%)。
- 旧结论基于重算前数据 + DB 饱和期的噪声,需作废。

### 信号 C — 失败根因指纹(MySQL 1040)

手术级精读 rainfall #26/#27/#28/#33 的 verifier detail,因果链一致:

```
sql_correctness → "exec failed: (1040, 'Too many connections')"   ← verifier 自己连不上
sql_executes    → {sql_count: 2, succeeded: 1, failed: 1}        ← agent execute_code 的 failed=1 即 1040
tool_trace_sanity → {failure_rate: 0.5}                          ← 同一 1040 计为工具失败
tool_stats      → execute_code count=2 success=1 failure=1
```

agent 的 `execute_code` 通常调 2 次:第 1 次(如 INFORMATION_SCHEMA 探查)撞 1040 失败,第 2 次重试成功。verifier 把"DB 连不上"当"agent 写错 SQL / 工具失败",在 sql_execution 和 trace 两层重复扣分。

**这解释了为何 62 fail 但 sql_safety 0 fail**:1040 是连接级失败,SQL 本身只读无害,所以安全检查照过。

---

## 手术级:真 SQL 落点(给反哺用的定位)

- `eval_results.*.json` 的 `actual_sql` 字段:大量为空(water-situation 前 14 case 全空),**不可作为"agent 没写 SQL"的证据**。
- 真 SQL 在 `messages/*.json` 的 assistant.tool_calls[func=execute_code].arguments 的 code 字符串里,形如 `sql = """SELECT ..."""`。`verifiers._extract_code_tool_calls` 能正确提取(已验证)。
- **反哺 SKILL.md 前必须读 messages,不能只读 eval_results。**

---

## 待独立验证的修复方向(非指令,供讨论)

1. **测量层 — 隔离 DB 饱和对 verifier 的污染**(最高优先级)
   - `sql_executes` / `tool_trace_sanity`:把 status 里的 `1040 Too many connections` / 连接级异常**单独归类为 infra-skip**,不计入 agent 失败率。需在 `_extract_code_tool_calls` 的 status 标注 + verifier 判定两处改。
   - 或:`sql_correctness` 已有连接复用 `_CONN_CACHE`(2026-06-24 加),但 `sql_executes` 走的是 agent 实际执行的 status,**不会复用**——1040 发生在 agent 跑的时候,verifier 事后只能看到"失败",无法区分。故根因是**重跑基线时 DB 必须空闲**。

2. **重采基线**:在 DB 无 1040 时段重跑 98 题(或用本地只读副本 / 离线 dump),拿到真实 sql_correctness 信号,再定 regression gate 门槛。现 `0.783` 是下界,真实值大概率更高。

3. **真业务信号(domain_coverage 21 fail)** 才是该反哺 skill 的:21 个 case 答案缺领域关键词,这是不依赖 DB 的真实失败,值得单独 triage。

4. **作废 memory 旧结论**:36 占位符污染 + water-situation 集中,在 1040 饱和下无法证实,需在新基线上重 triage。

---

## 附录:B1 修复 + B1.1 勘察(2026-06-25,post-fix)

**B1 已实施并提交(commit 5ccd13f75)**:verifiers.py 加 `_classify_failure(status,output)`,把 DB infra(MySQL 2013/2026/1045/超时/pymysql.connect 等)从 `sql_executes`/`tool_trace_sanity` 分母剔除(全 infra→skip=-1)。纯函数单测全过。绕库混合 aggregate 验证:**total 0.807→0.841 (+0.033),pass 0.929→0.949,sql_safety 零偏差(隔离干净)**。sql_error(1054/1064 真SQL bug)仍正确计失败。

**B1.1 勘察结论(前提证伪,取消)**:388 调用的最终 category 分布 = success 260 / infra 47 / sql_error 29 / other 52。原以为 other 是"截断",实测**无截断**(output median 250 字符)——52 条全是 status=error+Traceback 的 **agent 代码 bug**:ModuleNotFoundError 16 / TypeError 14 / 其他Python错 7 / SyntaxError 6 / KeyError 4 / query()参数错 4 / NameError 1。**全为真 agent 失败,不该 skip**(B1 正确保留)。故无改 verifier 的正确空间,B1.1 取消,转 A(诊断脚本)。

**反哺 skill 的金矿(待 A 沉淀)**:两类系统性 agent bug 模式 —— ① **ModuleNotFoundError 14 条**(agent 系统性漏写 `sys.path.insert` 直接 `from db import query`)→ skill 应更强教导入/lib 自动注入路径;② **query() 参数错 4 条**(误用 `db.query()` 签名)→ few_shots 补正确调用示例。另:`domain_coverage` 21 fail(不依赖 DB)是独立真实信号。

## 方法论笔记(为何这套思路有效)

HALO 的核心论点("通用 agent 对单条 trace 过拟合,需跨 case 找系统性模式")在此得到验证:
- 单看 rainfall#26(0.735),会以为是 agent SQL 有问题。
- 跨 98 case 聚合,发现 62 fail 共享同一 `1040` 指纹 → 指向管道而非 agent。
- 发现级聚合(几行统计)先暴露"一类 case 全跪",手术级再精读定位,避免逐题人工 triage 的误判。

**water-resources 落地建议**:把本报告的聚合逻辑固化成 `scripts/analyze_failures.py`(方案 A),作为 run_gate 之前的"诊断前置",与 verifier/gate 解耦。本次 PoC 证明其产出比人工 triage 系统得多。

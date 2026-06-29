# HALO 式跨 case 诊断报告

> 只读诊断 · 数据观察非指令 · 不连库不调LLM · 输入 `/opt/git/hermes-agent/skills/water-resources/reports/harness_baseline/eval_results_20260623_175514_corrected.json`
> 生成 2026-06-29 09:23

## TL;DR
⚠️ DB infra 故障占比 12% —— 基线受 DB 状态污染,先重采干净基线(B2)再判 skill

- total_score avg **0.807** / pass(≥0.6) **92.9%**(98 case)
- execute_code 调用 388 条:success 260 / infra 47 / sql_error 29 / other 52

## 1. 全局健康度(verifier 子项失败数)
- `tool_trace_sanity`: 81 fail  ← 测量管道嫌疑(需连DB层)
- `sql_executes`: 62 fail  ← 测量管道嫌疑(需连DB层)
- `domain_coverage`: 21 fail
- `sql_correctness`: 12 fail
- `numeric_presence`: 1 fail
- `response_validity`: 1 fail

## 2. 发现级:verifier 失败密度(per skill × layer)
| skill | final_answer | sql_execution | trace | policy |
|---|---|---|---|---|
| gate-pump-operation | 3/45 | 8/30 (skip15) | 12/15 | 0/15 |
| rainfall | 2/54 | 14/36 (skip18) | 18/18 | 0/18 |
| water-forecast | 5/39 | 11/26 (skip13) | 13/13 | 0/13 |
| water-quality | 3/39 | 7/26 (skip13) | 9/13 | 0/13 |
| water-situation | 6/75 | 24/50 (skip9) | 19/25 | 0/25 |
| water-warning | 4/42 | 10/28 (skip14) | 10/14 | 0/14 |

## 3. bug 类型聚类(category=other/sql_error 的 agent 代码错)
- **MySQL 1054**: 18 条 — water-situation#2, water-situation#4, water-situation#6
- **ModuleNotFoundError**: 16 条 — water-situation#9, rainfall#27, rainfall#31
- **TypeError**: 14 条 — water-situation#10, water-situation#14, water-situation#17
- **SyntaxError**: 6 条 — water-situation#24, rainfall#26, rainfall#33
- **其他/无指纹**: 5 条 — water-situation#13, water-situation#24, rainfall#34
- **MySQL 3024**: 4 条 — water-situation#9, water-quality#48, water-forecast#58
- **MySQL 1064**: 4 条 — water-situation#9, water-situation#14, gate-pump-operation#82
- **KeyError**: 4 条 — rainfall#43, water-quality#50, gate-pump-operation#70
- **query()参数错(unexpected keyword)**: 4 条 — water-quality#46, water-quality#56, water-forecast#64
- **ValueError**: 2 条 — water-quality#46, water-quality#48
- **MySQL 1052**: 2 条 — gate-pump-operation#71, gate-pump-operation#80
- **NameError**: 1 条 — water-quality#46
- **MySQL 2026**: 1 条 — water-warning#92

## 4. 系统性 agent bug 模式(反哺 skill 金矿,待独立验证)
- **ModuleNotFoundError 漏写 sys.path.insert** — 16 条 — agent 直接 `from db import query` 未先 insert lib 路径; skill 应更强教导入方式,或 lib 自动注入路径
- **query() 签名误用** — 4 条 — agent 误用 db.query() 参数;few_shots 应补正确调用示例
- **domain_coverage 缺领域关键词** — 20 case 答案缺领域关键词(不依赖 DB,真实业务信号,值得逐题 triage)

## 5. top 失败 case(总分最低,带一行证据)
- `water-quality#47` score=0.35 fail=[tool_trace_sanity] | 查询京杭运河水质站当前水质等级（单因子评价法）。
- `water-forecast#59` score=0.45 fail=[domain_coverage, sql_executes, tool_trace_sanity] | 预测未来24小时古运河水位站的水位变化趋势。
- `water-forecast#58` score=0.51 fail=[domain_coverage, tool_trace_sanity] | 查询最新预测任务的状态。
- `water-situation#22` score=0.53 fail=[tool_trace_sanity] | 查询水位站宝应这个月的水位数据（同义词测试：本月 = 当月）。
- `water-forecast#67` score=0.53 fail=[tool_trace_sanity] | 预测瘦西湖未来24小时水位变化。
- `gate-pump-operation#72` score=0.53 fail=[tool_trace_sanity] | 查询念四闸站最新的上下游水位和过闸流量。
- `water-quality#48` score=0.58 fail=[domain_coverage, sql_executes, tool_trace_sanity] | 查询所有水质站最新一条数据中，哪些指标劣于Ⅳ类。

## 方法论

HALO 思路:跨 case 聚合找系统性模式,而非逐题过拟合单条 trace。
失败集中在'需连 DB 才能判'的层(sql_executes/tool_trace/sql_correctness)= 测量管道指纹;
失败均匀分布 = agent 能力问题。`_classify_failure`(verifiers.py)区分 infra(非agent错)/sql_error(真SQL bug)/other(agent代码bug)。
**本报告是 trace evidence,非修复指令;反哺 skill 前务必读 messages/*.json 核实。**

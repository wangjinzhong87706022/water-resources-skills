#!/usr/bin/env python3
"""analyze_failures.py — HALO 式跨 case 诊断(只读,固化 PoC)。

在已落盘的 eval_results + messages 上做跨 case 聚合,产诊断报告 md(+json),
作为 run_gate 之前的"诊断前置":任何 skill 改动前先看真实失败分布,避免在
噪声/失真基线上盲目改 skill。

原则(HALO):只读诊断与执行分离 —— 只产数据观察 + case_id 证据,不给修复指令。
不连库、不调 LLM、不改 skill/verifier。verifier 分数直接读 eval_results 里已有的,
故 sql_correctness 等连库 verifier 用历史落盘值(不会卡 DB)。

用法:
  python3 analyze_failures.py [eval_results.json] [--messages-dir DIR] [--out OUT]
  # 默认: reports/harness_baseline 最新 eval_results_*.json(优先 _corrected)
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verifiers  # noqa: E402
from harness_adapter import _final_text_from_messages  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent  # water-resources/

# layer 别名(与 verifiers 一致)
LAYERS = ["final_answer", "sql_execution", "trace", "policy"]

# bug 类型指纹(category∈{other,sql_error} 时从 output 抽)
_BUG_PATTERNS = [
    ("ModuleNotFoundError", re.compile(r"ModuleNotFoundError")),
    ("query()参数错(unexpected keyword)", re.compile(r"unexpected keyword argument")),
    ("TypeError", re.compile(r"TypeError")),
    ("SyntaxError", re.compile(r"SyntaxError")),
    ("KeyError", re.compile(r"KeyError")),
    ("NameError", re.compile(r"NameError")),
    ("IndexError", re.compile(r"IndexError")),
    ("ValueError", re.compile(r"ValueError")),
]


def load_run(eval_path, msgs_dir):
    """读 eval_results 的 results + 对应 messages。学 recompute_verifiers._build_cases。"""
    data = json.load(open(eval_path))
    results = data["results"]
    msgs_map = {}
    for r in results:
        sk, idx = r["skill"], r["index"]
        mf = os.path.join(msgs_dir, f"{sk}_{idx:03d}.json")
        msgs_map[(sk, idx)] = json.load(open(mf)) if os.path.exists(mf) else []
    return data, results, msgs_map


def verifier_density(results):
    """per-skill × per-verifier-layer 失败密度:{skill:{layer:(fail,total,skip)}}。"""
    grid = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))  # skill→layer→[fail,total,skip]
    for r in results:
        sk = r["skill"]
        for v in (r.get("scores", {}).get("verifiers") or []):
            layer = v.get("layer", "?")
            sc = v.get("score")
            grid[sk][layer][1] += 1  # total
            if sc is not None and sc < 0:
                grid[sk][layer][2] += 1  # skip
            elif sc is not None and sc < 1.0:
                grid[sk][layer][0] += 1  # fail
    return grid


def category_breakdown(msgs_map):
    """对每条 execute_code 调用分类(复用 verifiers._extract_code_tool_calls 已含 category)。"""
    cats = Counter()
    for msgs in msgs_map.values():
        for c in verifiers._extract_code_tool_calls(msgs):
            cats[c.get("category", "other")] += 1
    return cats


def cluster_bug_types(msgs_map):
    """对 category∈{other,sql_error} 的调用,按错误类型聚类,带代表 case_id。"""
    clusters = defaultdict(lambda: {"count": 0, "cases": []})  # type → {count, cases}
    sql_code_counter = Counter()
    for (sk, idx), msgs in msgs_map.items():
        case_id = f"{sk}#{idx}"
        for c in verifiers._extract_code_tool_calls(msgs):
            if c.get("category") not in ("other", "sql_error"):
                continue
            out = c["output"] or ""
            matched = False
            for name, pat in _BUG_PATTERNS:
                if pat.search(out):
                    clusters[name]["count"] += 1
                    if len(clusters[name]["cases"]) < 3:
                        clusters[name]["cases"].append(case_id)
                    matched = True
                    break
            if not matched:
                # 退而求其次:MySQL error code
                codes = re.findall(r"\((\d{4})[,)\s]", out)
                if codes:
                    key = f"MySQL {codes[0]}"
                    clusters[key]["count"] += 1
                    if len(clusters[key]["cases"]) < 3:
                        clusters[key]["cases"].append(case_id)
                else:
                    clusters["其他/无指纹"]["count"] += 1
                    if len(clusters["其他/无指纹"]["cases"]) < 3:
                        clusters["其他/无指纹"]["cases"].append(case_id)
    return clusters


def systemic_patterns(results, clusters):
    """提炼跨 case 的系统性 agent bug 模式(反哺 skill 的金矿)。"""
    pats = []
    mnf = clusters.get("ModuleNotFoundError", {}).get("count", 0)
    if mnf >= 3:
        pats.append(("ModuleNotFoundError 漏写 sys.path.insert",
                     f"{mnf} 条 — agent 直接 `from db import query` 未先 insert lib 路径;"
                     " skill 应更强教导入方式,或 lib 自动注入路径"))
    qkw = clusters.get("query()参数错(unexpected keyword)", {}).get("count", 0)
    if qkw >= 2:
        pats.append(("query() 签名误用",
                     f"{qkw} 条 — agent 误用 db.query() 参数;few_shots 应补正确调用示例"))
    dc_fail = sum(1 for r in results for v in (r.get("scores", {}).get("verifiers") or [])
                  if v.get("name") == "domain_coverage" and 0 <= (v.get("score") or 1) < 1.0)
    if dc_fail >= 5:
        pats.append(("domain_coverage 缺领域关键词",
                     f"{dc_fail} case 答案缺领域关键词(不依赖 DB,真实业务信号,值得逐题 triage)"))
    return pats


def _skill_avg(results):
    """per-skill 平均 total_score。"""
    g = defaultdict(list)
    for r in results:
        if r.get("total_score") is not None:
            g[r["skill"]].append(r["total_score"])
    return {sk: sum(v) / len(v) for sk, v in g.items() if v}


def _verifier_fails(results):
    """{verifier_name: fail 数}。"""
    vn = Counter()
    for r in results:
        for v in (r.get("scores", {}).get("verifiers") or []):
            sc = v.get("score")
            if sc is not None and 0 <= sc < 1.0:
                vn[v["name"]] += 1
    return vn


def compare_runs(results_a, msgs_a, results_b, msgs_b, label_a, label_b):
    """两 run 的趋势对比 md 段。a=baseline, b=current。复用 category_breakdown。"""
    avg_a, avg_b = _skill_avg(results_a), _skill_avg(results_b)
    vf_a, vf_b = _verifier_fails(results_a), _verifier_fails(results_b)
    cat_a, cat_b = category_breakdown(msgs_a), category_breakdown(msgs_b)
    overall_a = sum(avg_a.values()) / len(avg_a) if avg_a else 0
    overall_b = sum(avg_b.values()) / len(avg_b) if avg_b else 0

    L = [f"## 6. 趋势对比:`{label_b}` vs `{label_a}`"]
    L.append(f"- 总 avg: {overall_a:.3f} → **{overall_b:.3f}** (Δ {overall_b - overall_a:+.3f})\n")
    L.append("### per-skill avg")
    L.append("| skill | " + label_a + " | " + label_b + " | Δ |")
    L.append("|---|---|---|---|")
    for sk in sorted(set(avg_a) | set(avg_b)):
        a, b = avg_a.get(sk, 0), avg_b.get(sk, 0)
        L.append(f"| {sk} | {a:.3f} | {b:.3f} | {b - a:+.3f} |")
    L.append("")
    L.append("### verifier 失败数(只列有变化的)")
    names = sorted(set(vf_a) | set(vf_b))
    shown = False
    for n in names:
        d = vf_b.get(n, 0) - vf_a.get(n, 0)
        if d != 0:
            L.append(f"- `{n}`: {vf_a.get(n, 0)} → {vf_b.get(n, 0)} (Δ {d:+d})")
            shown = True
    if not shown:
        L.append("- (无变化)")
    L.append("")
    L.append("### category 分布")
    L.append("| category | " + label_a + " | " + label_b + " | Δ |")
    L.append("|---|---|---|---|")
    for c in ("success", "infra", "sql_error", "other"):
        a, b = cat_a.get(c, 0), cat_b.get(c, 0)
        L.append(f"| {c} | {a} | {b} | {b - a:+d} |")
    L.append("")
    return "\n".join(L)


def render_report(data, results, msgs_map, eval_path):
    summary = data.get("summary", {})
    grid = verifier_density(results)
    cats = category_breakdown(msgs_map)
    clusters = cluster_bug_types(msgs_map)
    patterns = systemic_patterns(results, clusters)
    total_calls = sum(cats.values()) or 1

    totals = [r.get("total_score") for r in results if r.get("total_score") is not None]
    avg = sum(totals) / len(totals) if totals else 0
    pass_rate = sum(1 for t in totals if t >= 0.6) / len(totals) if totals else 0

    # 判最大失败源
    infra_ratio = cats.get("infra", 0) / total_calls
    if infra_ratio > 0.10:
        verdict = f"⚠️ DB infra 故障占比 {infra_ratio:.0%} —— 基线受 DB 状态污染,先重采干净基线(B2)再判 skill"
    elif patterns:
        verdict = f"基线基本可信;主要失败源是真实 agent bug({len(patterns)} 类系统性模式,见下)"
    else:
        verdict = "基线健康,失败分散,无明显系统性模式"

    L = []
    L.append("# HALO 式跨 case 诊断报告\n")
    L.append(f"> 只读诊断 · 数据观察非指令 · 不连库不调LLM · 输入 `{eval_path}`")
    L.append(f"> 生成 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    L.append(f"## TL;DR\n{verdict}\n")
    L.append(f"- total_score avg **{avg:.3f}** / pass(≥0.6) **{pass_rate:.1%}**({len(totals)} case)")
    L.append(f"- execute_code 调用 {total_calls} 条:success {cats.get('success',0)} / "
             f"infra {cats.get('infra',0)} / sql_error {cats.get('sql_error',0)} / other {cats.get('other',0)}\n")

    L.append("## 1. 全局健康度(verifier 子项失败数)")
    vn = Counter()
    for r in results:
        for v in (r.get("scores", {}).get("verifiers") or []):
            sc = v.get("score")
            if sc is not None and 0 <= sc < 1.0:
                vn[v["name"]] += 1
    for name, n in vn.most_common():
        flag = "  ← 测量管道嫌疑(需连DB层)" if name in ("sql_executes", "tool_trace_sanity") and n > 30 else ""
        L.append(f"- `{name}`: {n} fail{flag}")
    L.append("")

    L.append("## 2. 发现级:verifier 失败密度(per skill × layer)")
    skills = sorted(grid)
    L.append("| skill | " + " | ".join(LAYERS) + " |")
    L.append("|" + "---|" * (len(LAYERS) + 1))
    for sk in skills:
        cells = []
        for layer in LAYERS:
            f, t, s = grid[sk].get(layer, [0, 0, 0])
            cells.append(f"{f}/{t}" + (f" (skip{s})" if s else ""))
        L.append(f"| {sk} | " + " | ".join(cells) + " |")
    L.append("")

    L.append("## 3. bug 类型聚类(category=other/sql_error 的 agent 代码错)")
    if clusters:
        for name, info in sorted(clusters.items(), key=lambda x: -x[1]["count"]):
            cases = ", ".join(info["cases"])
            L.append(f"- **{name}**: {info['count']} 条 — {cases}")
    else:
        L.append("- (无)")
    L.append("")

    L.append("## 4. 系统性 agent bug 模式(反哺 skill 金矿,待独立验证)")
    if patterns:
        for name, desc in patterns:
            L.append(f"- **{name}** — {desc}")
    else:
        L.append("- (未发现跨 case 系统性模式)")
    L.append("")

    L.append("## 5. top 失败 case(总分最低,带一行证据)")
    bottom = sorted(results, key=lambda r: r.get("total_score") or 1)[:10]
    for r in bottom:
        ts = r.get("total_score")
        if ts is None or ts >= 0.6:
            continue
        failed = [v["name"] for v in (r.get("scores", {}).get("verifiers") or [])
                  if 0 <= (v.get("score") or 1) < 1.0]
        L.append(f"- `{r['skill']}#{r['index']}` score={ts:.2f} fail=[{', '.join(failed)[:60]}] | {r['question'][:40]}")
    L.append("")

    L.append("## 方法论\n")
    L.append("HALO 思路:跨 case 聚合找系统性模式,而非逐题过拟合单条 trace。")
    L.append("失败集中在'需连 DB 才能判'的层(sql_executes/tool_trace/sql_correctness)= 测量管道指纹;")
    L.append("失败均匀分布 = agent 能力问题。`_classify_failure`(verifiers.py)区分 infra(非agent错)/sql_error(真SQL bug)/other(agent代码bug)。")
    L.append("**本报告是 trace evidence,非修复指令;反哺 skill 前务必读 messages/*.json 核实。**\n")
    return "\n".join(L), {"avg": round(avg, 3), "pass_rate": round(pass_rate, 3),
                          "category": dict(cats), "bug_clusters": {k: v["count"] for k, v in clusters.items()},
                          "systemic_patterns": [p[0] for p in patterns]}


def main():
    ap = argparse.ArgumentParser(description="HALO 式跨 case 诊断(只读)")
    ap.add_argument("eval_results", nargs="?", default=None,
                    help="eval_results_*.json;默认 reports/harness_baseline 最新(优先 _corrected)")
    ap.add_argument("--messages-dir", default=None, help="messages 目录;默认 <eval 同目录>/messages")
    ap.add_argument("--out", default=None, help="输出 md 路径;默认 reports/halo_diag_<date>/diagnosis_report.md")
    ap.add_argument("--baseline-run", default=None,
                    help="对比基准 eval_results_*.json;给出则追加趋势对比段")
    ap.add_argument("--baseline-messages-dir", default=None,
                    help="对比基准的 messages 目录;默认 <baseline-run 同目录>/messages")
    args = ap.parse_args()

    if args.eval_results:
        eval_path = args.eval_results
    else:
        cands = [f for f in sorted(glob.glob(str(SKILL_ROOT / "reports" / "harness_baseline" / "eval_results_*.json")))]
        # 优先 _corrected
        corr = [f for f in cands if "_corrected" in f]
        eval_path = (corr or cands)[-1]
    msgs_dir = args.messages_dir or os.path.join(os.path.dirname(eval_path), "messages")

    data, results, msgs_map = load_run(eval_path, msgs_dir)
    md, j = render_report(data, results, msgs_map, eval_path)

    if args.baseline_run:
        b_msgs_dir = args.baseline_messages_dir or os.path.join(os.path.dirname(args.baseline_run), "messages")
        b_data, b_results, b_msgs = load_run(args.baseline_run, b_msgs_dir)
        md += "\n" + compare_runs(b_results, b_msgs, results, msgs_map,
                                  label_a=os.path.basename(args.baseline_run),
                                  label_b=os.path.basename(eval_path))
        j["comparison_vs"] = os.path.basename(args.baseline_run)

    out = args.out or str(SKILL_ROOT / "reports" / f"halo_diag_{datetime.now().strftime('%Y%m%d')}"
                          / "diagnosis_report.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(md)
    with open(os.path.splitext(out)[0] + ".json", "w") as f:
        json.dump(j, f, ensure_ascii=False, indent=2)
    print(f"✓ 诊断报告 → {out}")
    print(f"  avg={j['avg']} pass={j['pass_rate']} category={j['category']}")
    print(f"  systemic: {j['systemic_patterns']}")
    if args.baseline_run:
        print(f"  含趋势对比 vs {os.path.basename(args.baseline_run)}")


if __name__ == "__main__":
    main()

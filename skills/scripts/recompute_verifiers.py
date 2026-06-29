#!/usr/bin/env python3
"""离线重算 verifier:在已落盘的 trajectory(messages/*.json)上重跑全部 verifier,
不调 LLM、不重跑 agent。用于修正 sql_correctness 等 verifier 后回看真实分数。
DB 结果缓存到 _recompute_cache.pkl,改写入逻辑不必重连库。

用法: python3 scripts/recompute_verifiers.py [run_dir] [--write]
      run_dir 默认 reports/harness_baseline;--write 回写 <orig>_corrected.json
"""
import json, glob, os, sys, types, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verifiers
from harness_adapter import _final_text_from_messages

DB = {"host": "192.168.100.103", "port": 3306, "user": "root",
      "password": os.environ.get("SL323_DB_PASSWORD", ""), "database": "sl323"}


def _bucket(s):
    return "skip" if (s is None or s < 0) else str(round(s, 1))


def _build_cases(results, msgs_dir):
    cases = []
    for i, r in enumerate(results, 1):
        sk, idx = r["skill"], r["index"]
        mf = os.path.join(msgs_dir, f"{sk}_{idx:03d}.json")
        msgs = json.load(open(mf)) if os.path.exists(mf) else []
        ctx = verifiers.VerifierContext(
            case=types.SimpleNamespace(skill=sk, index=idx, question=r["question"]),
            final_response=_final_text_from_messages(msgs), raw_messages=msgs,
            trajectory=[], tool_stats={},
            expected_sql=r.get("expected_sql") or "", db_config=DB)
        vr = verifiers.run_verifiers(ctx)
        agg = verifiers.aggregate(vr)
        cases.append((r, vr, agg))
        if i % 10 == 0:
            print(f"  ...{i}/{len(results)}", file=sys.stderr)
    return cases


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    run_dir = args[0] if args else "reports/harness_baseline"
    res_file = [f for f in sorted(glob.glob(os.path.join(run_dir, "eval_results_*.json")))
                if "_corrected" not in f][-1]
    data = json.load(open(res_file))
    results = data["results"]
    msgs_dir = os.path.join(run_dir, "messages")

    cache = os.path.join(run_dir, "_recompute_cache.pkl")
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(res_file):
        cases_out = pickle.load(open(cache, "rb"))
        print(f"(缓存命中 {len(cases_out)} 题,跳过 DB)", file=sys.stderr)
    else:
        print(f"(连库重算 {len(results)} 题...)", file=sys.stderr)
        cases_out = _build_cases(results, msgs_dir)
        pickle.dump(cases_out, open(cache, "wb"))

    old_avg = sum(r["total_score"] for r, _, _ in cases_out) / len(cases_out)
    sc_old = {"1.0": 0, "0.5": 0, "0.2": 0, "skip": 0}
    sc_new = {"1.0": 0, "0.5": 0, "0.2": 0, "skip": 0}
    per_skill, new_scores, sanity = {}, [], 0
    for r, vr, agg in cases_out:
        osc = next((v["score"] for v in r["scores"]["verifiers"] if v["name"] == "sql_correctness"), None)
        nsc = next((v.score for v in vr if v.name == "sql_correctness"), None)
        sc_old[_bucket(osc)] += 1
        sc_new[_bucket(nsc)] += 1
        if next((v["score"] for v in r["scores"]["verifiers"] if v["name"] == "sql_safety"), None) != \
           next((v.score for v in vr if v.name == "sql_safety"), None):
            sanity += 1
        per_skill.setdefault(r["skill"], []).append(agg["total_score"])
        new_scores.append(agg["total_score"])

    new_avg = sum(new_scores) / len(new_scores)
    print("=" * 62)
    print(f"离线重算 {len(cases_out)} 题  (run: {run_dir})")
    print("=" * 62)
    print("\nsql_correctness 分布(题数):")
    print(f"  {'分':<6}{'旧':>6}{'新':>6}{'变化':>8}")
    for k in ["1.0", "0.5", "0.2", "skip"]:
        print(f"  {k:<6}{sc_old[k]:>6}{sc_new[k]:>6}{sc_new[k]-sc_old[k]:>+8}")
    print(f"\n总分 avg:  旧 {old_avg:.3f}  →  新 {new_avg:.3f}  (Δ {new_avg-old_avg:+.3f})")
    print(f"\n按 skill(新 avg):")
    print(f"  {'skill':<22}{'n':>4}{'新avg':>8}")
    for sk in sorted(per_skill):
        v = per_skill[sk]
        print(f"  {sk:<22}{len(v):>4}{sum(v)/len(v):>8.3f}")
    print(f"\n健全性: 非-SC verifier(sql_safety) 新旧不一致 = {sanity} (应为 0)")

    genuine = [(r, vr) for (r, vr, agg) in cases_out
               if next((v.score for v in vr if v.name == "sql_correctness"), -1) == 0.2]
    print(f"\n=== triage: 修正后仍 0.2 的真实 mismatch = {len(genuine)} 题 ===")
    _bysk = {}
    for r, vr in genuine:
        _bysk[r["skill"]] = _bysk.get(r["skill"], 0) + 1
    print("  按 skill:", dict(sorted(_bysk.items())))
    for r, vr in genuine[:12]:
        _d = next(v for v in vr if v.name == "sql_correctness").detail
        print(f"  Q{r['index']} [{r['skill']}] agent={_d.get('agent_rows')} exp={_d.get('expected_rows')} | {r['question'][:38]}")

    if "--write" not in sys.argv:
        print("\n(加 --write 回写 corrected eval_results)")
        return

    import copy, datetime, re as _re

    def _v2d(v):
        return {"name": v.name, "layer": v.layer, "score": v.score,
                "passed": v.passed, "weight": v.weight, "detail": v.detail, "error": v.error}

    cor = []
    for r, vr, agg in cases_out:
        r2 = copy.deepcopy(r)
        r2["scores"] = {"verifiers": [_v2d(v) for v in vr],
                        **{k: agg[k] for k in ("layer_scores", "passed_layers", "failed_layers", "hard_fail")}}
        r2["total_score"] = agg["total_score"]
        cor.append(r2)
    n = len(cor)
    avg = sum(x["total_score"] for x in cor) / n
    pass_rate = sum(1 for x in cor if x["total_score"] >= 0.6) / n

    def _vmean(name):
        vs = [next((v["score"] for v in x["scores"]["verifiers"] if v["name"] == name), None) for x in cor]
        vs = [v for v in vs if v is not None and v >= 0]
        return sum(vs) / len(vs) if vs else 0

    by_s, by_l, hf = {}, {}, 0
    for x in cor:
        by_s.setdefault(x["skill"], []).append(x["total_score"])
        by_l.setdefault(x.get("level", "?"), []).append(x["total_score"])
        if x["scores"].get("hard_fail"):
            hf += 1
    summary = {
        "total_cases": n, "avg_score": round(avg, 3), "pass_rate": round(pass_rate, 3),
        "valid_response_rate": round(_vmean("response_validity"), 3),
        "domain_data_rate": round(_vmean("domain_coverage"), 3),
        "numeric_data_rate": round(_vmean("numeric_presence"), 3),
        "hard_fail_count": hf,
        "by_skill": [{"skill": s, "count": len(v), "avg_score": round(sum(v)/len(v), 3),
                      "pass_rate": round(sum(1 for x in v if x >= 0.6)/len(v), 3)} for s, v in sorted(by_s.items())],
        "by_level": [{"level": l, "count": len(v), "avg_score": round(sum(v)/len(v), 3),
                      "pass_rate": round(sum(1 for x in v if x >= 0.6)/len(v), 3)} for l, v in sorted(by_l.items())],
    }
    meta = copy.deepcopy(data.get("meta", {}))
    meta["recomputed"] = ("verifier fix: sql_correctness 改 COUNT(*) 同口径; "
                          + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    out = {"meta": meta, "summary": summary, "results": cor}
    out_path = _re.sub(r"\.json$", "", res_file) + "_corrected.json"
    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=2)
    print(f"\n✓ 已回写 corrected 基线 → {out_path}")
    print(f"  summary: avg={summary['avg_score']} pass={summary['pass_rate']} hard_fail={hf}")


if __name__ == "__main__":
    main()

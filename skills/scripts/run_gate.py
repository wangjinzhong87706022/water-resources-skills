#!/usr/bin/env python3
"""run_gate.py — Skill 改动的 Selection/Regression Gate 入口。

流程:
1. backup 所有 SKILL.md + references + shared(skill 改动可能触及)
2. (candidate patch 应已手工应用) subprocess 调 evaluate_skills.py 跑 candidate
3. load candidate + baseline(已有 reports/<baseline>)的 results
4. selection_gate + regression_gate
5. 未过 → 把 failed/hard_fail case 写 failed_trajectories.jsonl(Rejected Buffer)
6. restore SKILL.md
7. 输出 gate_decision_<patch>.json

baseline 复用已有 eval run(不重跑);只跑 1 次 candidate。subprocess 调 evaluate_skills.py
而非 import(隔离 + 简单;编程式 evaluate_many 留作后续优化)。
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import gates

SKILL_ROOT = Path(__file__).resolve().parent.parent  # water-resources/
SCRIPTS = Path(__file__).resolve().parent
_SUBSKILLS = ["rainfall", "water-situation", "water-quality", "water-forecast",
              "water-warning", "gate-pump-operation", "water-fusion", "water-visualization"]


def _discover_skill_files():
    files = []
    for sk in _SUBSKILLS:
        sk_md = SKILL_ROOT / sk / "SKILL.md"
        if sk_md.exists():
            files.append(str(sk_md))
        ref = SKILL_ROOT / sk / "references"
        if ref.exists():
            files += [str(f) for f in ref.rglob("*") if f.is_file()]
    shared = SKILL_ROOT / "shared"
    files += [str(f) for f in shared.rglob("*.md") if f.is_file()]
    return files


def _backup(paths, backup_dir):
    backed = {}
    os.makedirs(backup_dir, exist_ok=True)
    for p in paths:
        if os.path.exists(p):
            dst = os.path.join(backup_dir, os.path.relpath(p, SKILL_ROOT).replace("/", "__"))
            shutil.copy2(p, dst)
            backed[p] = dst
    return backed


def _restore(backed):
    for p, dst in backed.items():
        shutil.copy2(dst, p)


def load_results(run_dir):
    fs = sorted(glob.glob(os.path.join(run_dir, "eval_results_*.json")))
    if not fs:
        raise FileNotFoundError(f"no eval_results_*.json in {run_dir}")
    return json.load(open(fs[-1]))["results"]


def run_eval_subprocess(output_dir, model, skill=None, level=None, rng=None, timeout=600):
    cmd = [sys.executable, str(SCRIPTS / "evaluate_skills.py"),
           "--engine", "harness", "--model", model,
           "--output", output_dir, "--timeout", str(timeout)]
    if skill:
        cmd += ["--skill", skill]
    if level:
        cmd += ["--level", level]
    if rng:
        cmd += ["--range", rng]
    print(f"  [run_eval] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description="Skill 改动的 Selection/Regression Gate")
    ap.add_argument("--patch-id", required=True, help="本次 skill 改动标识")
    ap.add_argument("--baseline-run", required=True, help="baseline 的 reports 目录(已有)")
    ap.add_argument("--candidate-run", default=None, help="已跑好的 candidate reports(省略则自动跑)")
    ap.add_argument("--model", default=None, help="[自动跑 candidate] 模型名")
    ap.add_argument("--skill", default=None)
    ap.add_argument("--level", default=None)
    ap.add_argument("--range", default=None, dest="rng")
    ap.add_argument("--output", default="reports/gate")
    ap.add_argument("--no-restore", action="store_true", help="调试:不自动 restore")
    ap.add_argument("--min-pass-rate", type=float, default=0.7)
    ap.add_argument("--max-regression", type=float, default=0.05)
    ap.add_argument("--timeout", type=int, default=300,
                    help="单题超时秒数(传给 evaluate_skills; 同时决定 max_iterations)")
    args = ap.parse_args()

    cfg = gates.GateConfig(min_pass_rate=args.min_pass_rate, max_regression=args.max_regression)
    os.makedirs(args.output, exist_ok=True)
    backup_dir = os.path.join(args.output, f"_backup_{args.patch_id}")

    # 1. backup
    backed = _backup(_discover_skill_files(), backup_dir)
    print(f"[1/5] backup {len(backed)} skill 文件 → {backup_dir}")

    candidate_dir = args.candidate_run or os.path.join(args.output, f"candidate_{args.patch_id}")
    try:
        # 2. candidate
        if args.candidate_run:
            print(f"[2/5] 使用已有 candidate: {args.candidate_run}")
        else:
            if not args.model:
                print("[ERROR] 自动跑 candidate 需要 --model(或用 --candidate-run 指定已跑好的)")
                sys.exit(1)
            print("[2/5] (skill patch 应已手工应用) 跑 candidate evaluate...")
            run_eval_subprocess(candidate_dir, args.model, args.skill, args.level, args.rng, timeout=args.timeout)

        # 3. gate
        print("[3/5] gate 判定")
        cand = load_results(candidate_dir)
        base = load_results(args.baseline_run)
        sel = gates.selection_gate(cand, cfg)
        reg = gates.regression_gate(cand, base, cfg)
        print(f"  selection : passed={sel.passed}  violations={sel.violations}")
        print(f"  regression: passed={reg.passed}  deltas={reg.deltas}")
        if reg.violations:
            print(f"             violations={reg.violations}")

        # 4. rejected buffer
        overall = sel.passed and reg.passed
        buffer_path = os.path.join(args.output, "failed_trajectories.jsonl")
        if not overall:
            failed = [r for r in cand if r.get("scores", {}).get("hard_fail") or r.get("total_score", 0) < 0.6]
            vn = "; ".join(sel.violations + reg.violations)
            for c in failed:
                gates.to_rejected_buffer(c, c.get("trajectory_path", ""),
                                         gate="selection+regression", violation=vn,
                                         buffer_path=buffer_path, patch_id=args.patch_id)
            print(f"[4/5] 写 {len(failed)} 个失败 case → {buffer_path}")
        else:
            print("[4/5] gate 通过,不写 buffer")

        # 5. decision
        decision = {
            "patch_id": args.patch_id, "overall_passed": overall,
            "selection": asdict(sel), "regression": asdict(reg),
        }
        dec_path = os.path.join(args.output, f"gate_decision_{args.patch_id}.json")
        json.dump(decision, open(dec_path, "w"), ensure_ascii=False, indent=2)
        print(f"[5/5] decision → {dec_path}")
        print(f"\n{'✅ PATCH 通过 gate' if overall else '❌ PATCH 被拒(见 violations)'}")
    finally:
        if not args.no_restore:
            _restore(backed)
            print(f"(restored {len(backed)} skill 文件)")


if __name__ == "__main__":
    main()

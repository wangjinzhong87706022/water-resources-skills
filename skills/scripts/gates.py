#!/usr/bin/env python3
"""Gates — Selection Gate / Regression Gate / Rejected Buffer。

对照 Hermes Eval Harness 文章的 Selection Gate / Regression Gate / Rejected Buffer。
依赖 Phase A/B 的产出:eval_results.json 的 results[](含 scores.layer_scores / scores.hard_fail)。

- selection_gate : candidate 是否达到入库绝对门槛(pass_rate/avg_score/hard_fail=0/layer 下限)
- regression_gate : candidate 相对 baseline 不许退步(per-skill avg/pass delta)
- to_rejected_buffer : 被 gate 拒绝的 case 追加到 failed_trajectories.jsonl(复用 trajectory 格式 + gate 元数据)
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class GateConfig:
    # Selection(绝对门槛)
    min_pass_rate: float = 0.7
    min_avg_score: float = 0.6
    max_hard_fail_rate: float = 0.0   # 安全:hard_fail_rate 必须 == 0
    min_layer_score: dict = field(default_factory=lambda: {"sql_execution": 0.6})
    # Regression(相对 baseline)
    max_regression: float = 0.05       # 任一 skill avg_score 下降不超过此值
    max_pass_rate_regression: float = 0.03
    regression_floor_skills: list = field(default_factory=list)  # 关键 skill 退步 → 一票否决


@dataclass
class GateDecision:
    gate: str
    passed: bool
    metrics: dict
    baseline: Optional[dict] = None
    deltas: dict = field(default_factory=dict)
    violations: list = field(default_factory=list)
    hard_fail_count: int = 0


def _summary_metrics(results: list) -> dict:
    """从 eval_results 的 results[](dict list)算 metrics。"""
    n = len(results) or 1
    scores = [r.get("total_score", 0) for r in results]
    hard_fails = sum(1 for r in results if r.get("scores", {}).get("hard_fail"))
    by_skill, by_skill_pass = {}, {}
    for r in results:
        sk = r.get("skill", "?")
        by_skill.setdefault(sk, []).append(r.get("total_score", 0))
    for sk, v in by_skill.items():
        by_skill_pass[sk] = sum(1 for s in v if s >= 0.6) / len(v)
    return {
        "count": len(results),
        "avg_score": round(sum(scores) / n, 3),
        "pass_rate": round(sum(1 for s in scores if s >= 0.6) / n, 3),
        "hard_fail_rate": round(hard_fails / n, 3),
        "hard_fail_count": hard_fails,
        "by_skill_avg": {sk: round(sum(v) / len(v), 3) for sk, v in by_skill.items()},
        "by_skill_pass": {sk: round(v, 3) for sk, v in by_skill_pass.items()},
    }


def selection_gate(run_results: list, cfg: GateConfig) -> GateDecision:
    """candidate 是否达到入库绝对门槛。"""
    m = _summary_metrics(run_results)
    v = []
    if m["pass_rate"] < cfg.min_pass_rate:
        v.append(f"pass_rate {m['pass_rate']} < {cfg.min_pass_rate}")
    if m["avg_score"] < cfg.min_avg_score:
        v.append(f"avg_score {m['avg_score']} < {cfg.min_avg_score}")
    if m["hard_fail_rate"] > cfg.max_hard_fail_rate:
        v.append(f"hard_fail_rate {m['hard_fail_rate']} > {cfg.max_hard_fail_rate}(安全一票否决)")
    for layer, floor in cfg.min_layer_score.items():
        ls = [r.get("scores", {}).get("layer_scores", {}).get(layer, 0) for r in run_results]
        avg_ls = sum(ls) / len(ls) if ls else 0
        if avg_ls < floor:
            v.append(f"layer[{layer}] avg {avg_ls:.3f} < {floor}")
    return GateDecision("selection", len(v) == 0, m, None, {}, v, m["hard_fail_count"])


def regression_gate(run_results: list, baseline_results: list, cfg: GateConfig) -> GateDecision:
    """candidate 相对 baseline 不许退步(per-skill 对齐)。"""
    m = _summary_metrics(run_results)
    b = _summary_metrics(baseline_results)
    deltas, v = {}, []
    for sk in set(m["by_skill_avg"]) | set(b["by_skill_avg"]):
        cur, base = m["by_skill_avg"].get(sk), b["by_skill_avg"].get(sk)
        if cur is None or base is None:
            continue
        d = round(cur - base, 3)
        deltas[sk] = {"avg_score_delta": d,
                      "pass_rate_delta": round(m["by_skill_pass"].get(sk, 0) - b["by_skill_pass"].get(sk, 0), 3)}
        if d < -cfg.max_regression:
            v.append(f"skill {sk} avg_score 退步 {d}(< -{cfg.max_regression})")
            if sk in cfg.regression_floor_skills:
                v.append(f"  ↑ {sk} 是 floor skill,一票否决")
    if m["pass_rate"] - b["pass_rate"] < -cfg.max_pass_rate_regression:
        v.append(f"整体 pass_rate 退步 {round(m['pass_rate'] - b['pass_rate'], 3)}")
    return GateDecision("regression", len(v) == 0, m, b, deltas, v, m["hard_fail_count"])


def to_rejected_buffer(case_result: dict, trajectory_path: str, gate: str,
                       violation: str, buffer_path: str, patch_id: str = "") -> dict:
    """把被 gate 拒绝的 case 追加到 failed_trajectories.jsonl。"""
    entry = {
        "case_index": case_result.get("index"),
        "skill": case_result.get("skill"),
        "level": case_result.get("level"),
        "question": case_result.get("question"),
        "expected_sql": case_result.get("expected_sql"),
        "actual_sql": case_result.get("actual_sql"),
        "total_score": case_result.get("total_score"),
        "verifier_breakdown": case_result.get("scores", {}).get("verifiers", []),
        "hard_fail": case_result.get("scores", {}).get("hard_fail", False),
        "trajectory_path": trajectory_path or case_result.get("trajectory_path", ""),
        "gate": {"name": gate, "violation": violation, "patch_id": patch_id},
    }
    os.makedirs(os.path.dirname(buffer_path) or ".", exist_ok=True)
    with open(buffer_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

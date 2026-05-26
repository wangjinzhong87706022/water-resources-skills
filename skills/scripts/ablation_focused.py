#!/usr/bin/env python3
"""
消融实验（聚焦版）— 针对 no-dual-graph 和 no-adaptive 设计专项测试

针对性测试集:
  - 时间粒度测试（4题）: 需要 HOUR 级别对齐，固定 DAY 粒度会丢失信息
  - 执行策略测试（4题）: 涉及3+个独立 Skill，串行化影响效率

用法:
  python ablation_focused.py  # 运行 full + no-dual-graph + no-adaptive
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── 专项测试题 ────────────────────────────────────────────────

# 时间粒度测试：需要 HOUR 级别对齐，固定 DAY 粒度会丢失细节
TIME_GRANULARITY_TESTS = [
    {
        "id": "TG1",
        "question": "过去24小时古运河水位的逐小时变化趋势，以及对应时段的降雨情况",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨"],
        "fusion_type": "时间对齐(HOUR)",
        "granularity_hint": "逐小时",
    },
    {
        "id": "TG2",
        "question": "今天白天8点到18点古运河水位和降雨的逐小时对比分析",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨"],
        "fusion_type": "时间对齐(HOUR)",
        "granularity_hint": "逐小时",
    },
    {
        "id": "TG3",
        "question": "分析最近一次降雨过程中古运河水位的响应过程，需要小时级别的变化趋势",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨", "响应"],
        "fusion_type": "业务逻辑",
        "granularity_hint": "小时级别",
    },
    {
        "id": "TG4",
        "question": "查询古运河今日各小时水位和对应降雨量的变化趋势",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨"],
        "fusion_type": "时间对齐(HOUR)",
        "granularity_hint": "各小时",
    },
]

# 执行策略测试：涉及3+个独立Skill，串行化会影响效率
EXECUTION_STRATEGY_TESTS = [
    {
        "id": "ES1",
        "question": "同时查询扬州市所有河道最新水位、所有雨量站最新降雨量和各闸站最新运行状态",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨", "闸", "泵"],
        "fusion_type": "并行查询",
        "involved_skills": ["water-situation", "rainfall", "gate-pump-operation"],
    },
    {
        "id": "ES2",
        "question": "综合报告：古运河水位、瘦西湖水质、城区降雨量、各闸泵运行状态",
        "skills": "water-fusion",
        "expected_domains": ["水位", "水质", "降雨", "闸"],
        "fusion_type": "并行查询",
        "involved_skills": ["water-situation", "water-quality", "rainfall", "gate-pump-operation"],
    },
    {
        "id": "ES3",
        "question": "查询古运河上游和下游的水位，同时查询沿线各闸站运行情况和附近雨量站降雨",
        "skills": "water-fusion",
        "expected_domains": ["水位", "闸", "降雨"],
        "fusion_type": "空间+并行",
        "involved_skills": ["water-situation", "gate-pump-operation", "rainfall"],
    },
    {
        "id": "ES4",
        "question": "扬州市防洪调度综合评估：实时水位、累计降雨、闸泵调度、水质状况和预警信息",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨", "闸", "水质", "预警"],
        "fusion_type": "5域并行",
        "involved_skills": ["water-situation", "rainfall", "gate-pump-operation", "water-quality", "water-warning"],
    },
]

ALL_FOCUSED_TESTS = TIME_GRANULARITY_TESTS + EXECUTION_STRATEGY_TESTS

LIB_DIR = Path("/opt/git/hermes-agent/skills/water-resources/lib")
FUSION_PY = LIB_DIR / "fusion.py"
PLANNER_PY = LIB_DIR / "planner.py"
_originals = {}

CONFIG_LABELS = {
    "full": "完整系统",
    "no-dual-graph": "无双图分离(A)",
    "no-adaptive": "无自适应粒度(B)",
}


def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _file_hash(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()[:12]


def _log(msg):
    print(f"[{_ts()}] {msg}", flush=True)


def backup_originals():
    _originals["fusion"] = FUSION_PY.read_text()
    _originals["planner"] = PLANNER_PY.read_text()
    _log(f"备份原始文件: fusion={_file_hash(FUSION_PY)}, planner={_file_hash(PLANNER_PY)}")


def restore_originals():
    if "fusion" in _originals:
        FUSION_PY.write_text(_originals["fusion"])
    if "planner" in _originals:
        PLANNER_PY.write_text(_originals["planner"])
    _log(f"已恢复原始文件: fusion={_file_hash(FUSION_PY)}, planner={_file_hash(PLANNER_PY)}")


def apply_no_dual_graph():
    planner_code = _originals["planner"]
    old_block = re.search(
        r'BUSINESS_DEPENDENCIES\s*=\s*\{[^}]+\}',
        planner_code, re.DOTALL
    ).group()
    mutation = '''BUSINESS_DEPENDENCIES = {
    "rainfall":            ["water-situation"],
    "water-situation":     ["water-warning"],
    "water-quality":       ["water-warning"],
    "water-forecast":      ["water-situation"],
    "gate-pump-operation": ["water-situation"],
    "water-warning":       [],
}'''
    mutated = planner_code.replace(old_block, mutation)
    PLANNER_PY.write_text(mutated)


def apply_no_adaptive_granularity():
    fusion_code = _originals["fusion"]
    mutated = fusion_code.replace(
        '''                    if avg < 600:
                        gran = "MINUTE"
                    elif avg < 7200:
                        gran = "HOUR"
                    elif avg < 172800:
                        gran = "DAY"
                    else:
                        gran = "MONTH"''',
        '''                    gran = "DAY"  # Ablation: 固定DAY粒度'''
    )
    FUSION_PY.write_text(mutated)


CONFIG_MAP = {
    "full": None,
    "no-dual-graph": apply_no_dual_graph,
    "no-adaptive": apply_no_adaptive_granularity,
}


def run_hermes(prompt, skill, timeout=600):
    cmd = ["hermes", "-z", prompt, "-s", skill]
    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "HERMES_YOLO_MODE": "1", "HERMES_ACCEPT_HOOKS": "1"},
        )
        duration = time.time() - start
        response = result.stdout.strip()
        exit_code = result.returncode
        if not response and result.stderr:
            response = f"[STDERR]: {result.stderr.strip()}"
        if exit_code != 0 and result.stderr:
            _log(f"    hermes exit={exit_code}, stderr={result.stderr.strip()[:200]}")
        return response, duration, exit_code
    except subprocess.TimeoutExpired as e:
        partial = e.stdout.decode() if e.stdout else ""
        return f"[TIMEOUT after {timeout}s] partial={partial[:200]}", time.time() - start, -1
    except Exception as e:
        return f"[ERROR]: {e}", time.time() - start, -2


def evaluate_response(test, response, duration):
    scores = {}

    # 有效性
    if not response or response.startswith("[STDERR]") or response.startswith("[ERROR") or response.startswith("[TIMEOUT"):
        scores["valid_response"] = 0.0
    elif len(response) > 100:
        scores["valid_response"] = 1.0
    else:
        scores["valid_response"] = 0.5

    # 域完整性
    expected = test["expected_domains"]
    domain_hits = [kw for kw in expected if kw in response]
    domain_ratio = len(domain_hits) / len(expected) if expected else 0
    scores["domain_completeness"] = round(domain_ratio, 2)

    # 融合质量
    fusion_keywords = [
        "影响", "关联", "因果", "相关", "导致", "对比", "综合", "分析",
        "上涨", "下降", "变化", "趋势", "响应", "涨幅", "回落",
        "融合策略", "对齐", "空间对齐", "时间对齐",
        "逐小时", "小时", "小时级",
    ]
    fusion_hits = [kw for kw in fusion_keywords if kw in response]
    if len(test["expected_domains"]) > 1:
        scores["fusion_quality"] = min(1.0, len(fusion_hits) / 3.0)
    else:
        scores["fusion_quality"] = 1.0

    # 时间粒度准确性（针对 TG 测试）
    granularity_hint = test.get("granularity_hint", "")
    if granularity_hint:
        # 检查是否包含小时级别的时间表达
        hour_indicators = ["时", "小时", ":00", "时段", "逐小时", "每小时", "小时级"]
        hour_hits = [kw for kw in hour_indicators if kw in response]
        scores["granularity_accuracy"] = 1.0 if len(hour_hits) >= 2 else 0.5 if len(hour_hits) >= 1 else 0.0
    else:
        scores["granularity_accuracy"] = -1  # 不适用

    # 数值数据
    numbers = re.findall(r"\d+\.?\d*", response)
    scores["has_numeric"] = 1.0 if len(numbers) >= 3 else 0.5 if len(numbers) >= 1 else 0.0

    # 加权总分
    if scores["granularity_accuracy"] >= 0:
        # 有粒度要求的测试：加入粒度准确度权重
        total = (
            scores["valid_response"] * 0.10
            + scores["domain_completeness"] * 0.25
            + scores["fusion_quality"] * 0.25
            + scores["granularity_accuracy"] * 0.25
            + scores["has_numeric"] * 0.15
        )
    else:
        total = (
            scores["valid_response"] * 0.15
            + scores["domain_completeness"] * 0.35
            + scores["fusion_quality"] * 0.30
            + scores["has_numeric"] * 0.20
        )
    scores["total"] = round(total, 2)

    return {
        "id": test["id"], "question": test["question"],
        "test_category": "时间粒度" if "granularity_hint" in test else "执行策略",
        "duration_sec": round(duration, 1), "scores": scores,
        "response_preview": response[:300] + "..." if len(response) > 300 else response,
        "response_length": len(response),
    }


def run_all_tests(timeout=600):
    results = []
    total = len(ALL_FOCUSED_TESTS)
    for i, test in enumerate(ALL_FOCUSED_TESTS):
        _log(f"  [{i+1}/{total}] {test['id']}: {test['question'][:60]}...")
        response, duration, exit_code = run_hermes(test["question"], test["skills"], timeout)
        result = evaluate_response(test, response, duration)
        result["exit_code"] = exit_code
        results.append(result)

        gran_str = f" gran={result['scores']['granularity_accuracy']:.1f}" if result['scores']['granularity_accuracy'] >= 0 else ""
        _log(f"  [{i+1}/{total}] → score={result['scores']['total']:.2f} "
             f"domain={result['scores']['domain_completeness']:.2f} "
             f"fusion={result['scores']['fusion_quality']:.2f}{gran_str} "
             f"({result['duration_sec']}s)")

    return results


def compute_summary(results):
    scores = [r["scores"]["total"] for r in results]
    domain_comp = [r["scores"]["domain_completeness"] for r in results]
    fusion_q = [r["scores"]["fusion_quality"] for r in results]
    durations = [r["duration_sec"] for r in results]
    gran_scores = [r["scores"]["granularity_accuracy"] for r in results if r["scores"]["granularity_accuracy"] >= 0]
    return {
        "avg_score": round(sum(scores) / len(scores), 3),
        "avg_domain_completeness": round(sum(domain_comp) / len(domain_comp), 3),
        "avg_fusion_quality": round(sum(fusion_q) / len(fusion_q), 3),
        "avg_granularity_accuracy": round(sum(gran_scores) / len(gran_scores), 3) if gran_scores else -1,
        "pass_rate": round(sum(1 for s in scores if s >= 0.6) / len(scores), 3),
        "total_duration": round(sum(durations), 1),
        "avg_duration_per_test": round(sum(durations) / len(durations), 1),
    }


def compute_category_summary(results, category):
    cat_results = [r for r in results if r["test_category"] == category]
    if not cat_results:
        return None
    return compute_summary(cat_results)


def run_config(config_name, timeout=600):
    label = CONFIG_LABELS.get(config_name, config_name)
    _log(f"\n{'='*60}")
    _log(f"配置: {config_name} ({label})")
    _log(f"{'='*60}")

    restore_originals()

    applier = CONFIG_MAP.get(config_name)
    if applier:
        applier()
        _log(f"  已应用 mutation: {config_name}")
        _log(f"  fusion hash={_file_hash(FUSION_PY)}, planner hash={_file_hash(PLANNER_PY)}")
    else:
        _log(f"  使用完整系统（无 mutation）")

    config_start = time.time()
    results = run_all_tests(timeout)
    summary = compute_summary(results)

    tg_summary = compute_category_summary(results, "时间粒度")
    es_summary = compute_category_summary(results, "执行策略")

    elapsed = time.time() - config_start
    _log(f"  结果: avg={summary['avg_score']:.3f}, "
         f"domain={summary['avg_domain_completeness']:.3f}, "
         f"fusion={summary['avg_fusion_quality']:.3f}, "
         f"gran={summary['avg_granularity_accuracy']:.3f}, "
         f"elapsed={elapsed:.0f}s")

    return {
        "config": config_name,
        "label": label,
        "summary": summary,
        "tg_summary": tg_summary,
        "es_summary": es_summary,
        "results": results,
        "config_duration_sec": round(elapsed, 1),
    }


def main():
    _log("=" * 60)
    _log("消融实验（聚焦版）— 专项测试 no-dual-graph + no-adaptive")
    _log(f"测试题数: {len(ALL_FOCUSED_TESTS)} (时间粒度{len(TIME_GRANULARITY_TESTS)}题 + 执行策略{len(EXECUTION_STRATEGY_TESTS)}题)")
    _log(f"配置数: 3 (full + no-dual-graph + no-adaptive)")
    _log("=" * 60)

    overall_start = time.time()
    backup_originals()

    configs = ["full", "no-dual-graph", "no-adaptive"]
    all_data = []

    try:
        for config in configs:
            data = run_config(config, 600)
            all_data.append(data)

        restore_originals()

        # 保存报告
        output_dir = Path("/opt/git/hermes-agent/skills/water-resources/reports/ablation")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"ablation_focused_{timestamp}.json"

        report_data = {
            "timestamp": timestamp,
            "total_elapsed_sec": round(time.time() - overall_start, 1),
            "test_type": "focused",
            "configs": all_data,
        }
        with open(report_path, "w") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # 打印对比表
        full = all_data[0]
        _log(f"\n{'='*80}")
        _log("聚焦消融实验结果对比")
        _log(f"{'='*80}")

        # 综合得分对比
        _log(f"\n{'配置':<20} {'平均分':>8} {'域完整':>8} {'融合质量':>8} {'粒度准确':>8} {'通过率':>8} {'耗时':>8}")
        _log("-" * 80)
        for d in all_data:
            s = d["summary"]
            gran_str = f"{s['avg_granularity_accuracy']:>8.3f}" if s["avg_granularity_accuracy"] >= 0 else "    N/A"
            _log(f"{d['config']:<20} {s['avg_score']:>8.3f} {s['avg_domain_completeness']:>8.3f} "
                  f"{s['avg_fusion_quality']:>8.3f} {gran_str} {s['pass_rate']:>8.1%} {s['total_duration']:>7.1f}s")

        # 分类对比：时间粒度测试
        _log(f"\n--- 时间粒度测试（TG1-TG4）---")
        _log(f"{'配置':<20} {'TG平均分':>10} {'粒度准确':>10} {'融合质量':>10}")
        _log("-" * 55)
        for d in all_data:
            if d["tg_summary"]:
                tgs = d["tg_summary"]
                _log(f"{d['config']:<20} {tgs['avg_score']:>10.3f} {tgs['avg_granularity_accuracy']:>10.3f} {tgs['avg_fusion_quality']:>10.3f}")

        # 分类对比：执行策略测试
        _log(f"\n--- 执行策略测试（ES1-ES4）---")
        _log(f"{'配置':<20} {'ES平均分':>10} {'平均耗时':>10}")
        _log("-" * 45)
        for d in all_data:
            if d["es_summary"]:
                ess = d["es_summary"]
                _log(f"{d['config']:<20} {ess['avg_score']:>10.3f} {ess['avg_duration_per_test']:>9.1f}s")

        # 贡献度
        _log(f"\n各创新点贡献（Full - Ablated）:")
        labels = {
            "no-dual-graph": "双图分离",
            "no-adaptive": "自适应粒度",
        }
        for d in all_data[1:]:
            label = labels.get(d["config"], d["config"])
            score_diff = full["summary"]["avg_score"] - d["summary"]["avg_score"]
            fusion_diff = full["summary"]["avg_fusion_quality"] - d["summary"]["avg_fusion_quality"]
            gran_full = full["summary"]["avg_granularity_accuracy"]
            gran_ablated = d["summary"]["avg_granularity_accuracy"]
            gran_diff = gran_full - gran_ablated if gran_full >= 0 and gran_ablated >= 0 else 0
            sign_s = "+" if score_diff > 0 else ""
            sign_f = "+" if fusion_diff > 0 else ""
            sign_g = "+" if gran_diff > 0 else ""
            _log(f"  {label:12s}: 分数{sign_s}{score_diff:.3f}  融合{sign_f}{fusion_diff:.3f}  粒度{sign_g}{gran_diff:.3f}")

        _log(f"\n报告: {report_path}")

    except Exception as e:
        restore_originals()
        _log(f"\n[ERROR] {e}")
        import traceback
        _log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()

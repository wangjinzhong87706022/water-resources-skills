#!/usr/bin/env python3
"""
消融实验 (Ablation Study) — 验证各创新点的独立贡献

用法:
  python ablation_fusion.py --config full        # 完整系统
  python ablation_fusion.py --config no-dual-graph # 无双图分离(A)
  python ablation_fusion.py --config no-adaptive   # 无自适应粒度(B)
  python ablation_fusion.py --config no-normalize  # 无站名归一化(C)
  python ablation_fusion.py --config no-conflict   # 无冲突检测(D)
  python ablation_fusion.py --config no-fusion     # 无融合(E)
  python ablation_fusion.py --all                  # 跑全部6组

实验设计:
  Full:       完整系统
  A:          因果关联→执行依赖（不使用双图分离）
  B:          固定DAY粒度（不自适应推断）
  C:          不做站名归一化（原始站名匹配）
  D:          跳过冲突检测和消解
  E:          简单拼接（不做关联分析和融合）

测试集: 8道跨域融合测试题（来自 autoresearch-fusion.py）
"""

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 复用跨域测试题
FUSION_TESTS = [
    {"id": "F1", "question": "综合查询古运河水位和降雨情况",
     "skills": "water-fusion", "expected_domains": ["水位", "降雨"], "fusion_type": "时间对齐"},
    {"id": "F2", "question": "分析最近降雨对古运河水位的影响",
     "skills": "water-fusion", "expected_domains": ["水位", "降雨"], "fusion_type": "业务逻辑"},
    {"id": "F3", "question": "查询古运河实时水位，并判断是否超过警戒水位",
     "skills": "water-fusion", "expected_domains": ["水位", "警戒"], "fusion_type": "业务逻辑"},
    {"id": "F4", "question": "查询瘦西湖最新水质数据，判断水质等级",
     "skills": "water-fusion", "expected_domains": ["水质", "等级"], "fusion_type": "业务逻辑"},
    {"id": "F5", "question": "查询古运河沿线水位及附近闸站运行情况",
     "skills": "water-fusion", "expected_domains": ["水位", "闸", "泵"], "fusion_type": "空间对齐"},
    {"id": "F6", "question": "扬州市防洪形势综合分析：当前水位、降雨、闸泵运行和预警状态",
     "skills": "water-fusion", "expected_domains": ["水位", "降雨", "闸", "泵", "预警"], "fusion_type": "混合"},
    {"id": "F7", "question": "2024年8月扬州城区降雨量最大的那天，各重点河道水位是否超警戒",
     "skills": "water-fusion", "expected_domains": ["降雨", "水位", "警戒"], "fusion_type": "时间对齐"},
    {"id": "F8", "question": "查询古运河最新水位",
     "skills": "water-situation", "expected_domains": ["水位"], "fusion_type": "单域"},
]

LIB_DIR = Path("/opt/git/hermes-agent/skills/water-resources/lib")
FUSION_PY = LIB_DIR / "fusion.py"
PLANNER_PY = LIB_DIR / "planner.py"

# 保存原始文件内容
_originals = {}

CONFIG_LABELS = {
    "full":         "完整系统",
    "no-dual-graph": "无双图分离(A)",
    "no-adaptive":  "无自适应粒度(B)",
    "no-normalize": "无站名归一化(C)",
    "no-conflict":  "无冲突检测(D)",
    "no-fusion":    "无融合(E)",
}


def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _file_hash(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()[:12]


def _log(msg):
    print(f"[{_ts()}] {msg}", flush=True)


def backup_originals():
    """备份原始文件"""
    _originals["fusion"] = FUSION_PY.read_text()
    _originals["planner"] = PLANNER_PY.read_text()
    _log(f"备份原始文件: fusion={_file_hash(FUSION_PY)}, planner={_file_hash(PLANNER_PY)}")


def restore_originals():
    """恢复原始文件"""
    if "fusion" in _originals:
        FUSION_PY.write_text(_originals["fusion"])
    if "planner" in _originals:
        PLANNER_PY.write_text(_originals["planner"])
    _log(f"已恢复原始文件: fusion={_file_hash(FUSION_PY)}, planner={_file_hash(PLANNER_PY)}")


# ── Mutation 函数 ──────────────────────────────────────────────

def apply_no_dual_graph():
    """配置A: 将因果关联转为执行依赖（模拟单一依赖图）"""
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
    """配置B: 固定 DAY 粒度，跳过自适应推断"""
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


def apply_no_normalize():
    """配置C: 站名不做归一化"""
    fusion_code = _originals["fusion"]
    mutated = fusion_code.replace(
        '''def normalize_station(name):
    if not isinstance(name, str):
        return str(name)
    for s in _SUFFIXES:
        if name.endswith(s):
            return name[:-len(s)]
    return name''',
        '''def normalize_station(name):
    # Ablation: 不做站名归一化
    return str(name) if not isinstance(name, str) else name'''
    )
    FUSION_PY.write_text(mutated)


def apply_no_conflict():
    """配置D: 冲突检测和消解直接返回空"""
    fusion_code = _originals["fusion"]
    mutated = fusion_code.replace(
        '''def detect_conflicts(fused_data):
    """Detect value conflicts in fused data.

    Returns list of conflicts with field, values, difference, threshold.
    """
    if not fused_data:
        return []

    conflicts = []''',
        '''def detect_conflicts(fused_data):
    """Detect value conflicts in fused data."""
    # Ablation: 跳过冲突检测
    return []'''
    )
    FUSION_PY.write_text(mutated)


def apply_no_fusion():
    """配置E: 融合函数直接返回简单拼接"""
    fusion_code = _originals["fusion"]
    mutated = fusion_code.replace(
        '''def correlate(results):
    """Identify multi-dimensional correlations between skill results.''',
        '''def correlate(results):
    # Ablation: 不做关联分析
    return {"time": [], "spatial": [], "business": []}

def _correlate_original(results):
    """Identify multi-dimensional correlations between skill results.'''
    )
    mutated = mutated.replace(
        '''def fuse(results, correlations, strategy="auto"):
    """Fuse multi-skill results using identified correlations.''',
        '''def fuse(results, correlations, strategy="auto"):
    # Ablation: 直接拼接不做融合
    return {"data": _concat_results(results), "strategy_used": "none", "fusion_points": []}

def _fuse_original(results, correlations, strategy="auto"):
    """Fuse multi-skill results using identified correlations.'''
    )
    FUSION_PY.write_text(mutated)


CONFIG_MAP = {
    "full": None,           # 不修改，使用完整系统
    "no-dual-graph": apply_no_dual_graph,     # A
    "no-adaptive": apply_no_adaptive_granularity,  # B
    "no-normalize": apply_no_normalize,       # C
    "no-conflict": apply_no_conflict,         # D
    "no-fusion": apply_no_fusion,             # E
}

# ── 测试执行 ──────────────────────────────────────────────────

def run_hermes(prompt: str, skill: str, timeout: int = 600) -> tuple[str, float, int]:
    """执行 hermes -z 并返回 (response, duration, exit_code)"""
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


def evaluate_response(test: dict, response: str, duration: float) -> dict:
    scores = {}

    if not response or response.startswith("[STDERR]") or response.startswith("[ERROR") or response.startswith("[TIMEOUT"):
        scores["valid_response"] = 0.0
    elif len(response) > 100:
        scores["valid_response"] = 1.0
    else:
        scores["valid_response"] = 0.5

    expected = test["expected_domains"]
    domain_hits = [kw for kw in expected if kw in response]
    domain_ratio = len(domain_hits) / len(expected) if expected else 0
    scores["domain_completeness"] = round(domain_ratio, 2)
    scores["domain_hits"] = domain_hits
    scores["domain_misses"] = [kw for kw in expected if kw not in response]

    fusion_keywords = [
        "影响", "关联", "因果", "相关", "导致", "对比", "综合", "分析",
        "上涨", "下降", "变化", "趋势", "响应", "涨幅", "回落",
        "融合策略", "对齐", "空间对齐", "时间对齐",
    ]
    fusion_hits = [kw for kw in fusion_keywords if kw in response]
    if len(test["expected_domains"]) > 1:
        scores["fusion_quality"] = min(1.0, len(fusion_hits) / 3.0)
    else:
        scores["fusion_quality"] = 1.0
    scores["fusion_keywords_found"] = fusion_hits

    numbers = re.findall(r"\d+\.?\d*", response)
    scores["has_numeric"] = 1.0 if len(numbers) >= 3 else 0.5 if len(numbers) >= 1 else 0.0

    total = (
        scores["valid_response"] * 0.15
        + scores["domain_completeness"] * 0.35
        + scores["fusion_quality"] * 0.30
        + scores["has_numeric"] * 0.20
    )
    scores["total"] = round(total, 2)

    return {
        "id": test["id"], "question": test["question"],
        "duration_sec": round(duration, 1), "scores": scores,
        "response_preview": response[:300] + "..." if len(response) > 300 else response,
        "response_length": len(response),
    }


def run_all_tests(timeout: int = 600) -> list[dict]:
    results = []
    total = len(FUSION_TESTS)
    config_start = time.time()
    for i, test in enumerate(FUSION_TESTS):
        _log(f"  [{i+1}/{total}] {test['id']}: {test['question'][:60]}...")
        response, duration, exit_code = run_hermes(test["question"], test["skills"], timeout)
        result = evaluate_response(test, response, duration)
        result["exit_code"] = exit_code
        results.append(result)

        miss_str = f" | 缺失域: {result['scores']['domain_misses']}" if result['scores']['domain_misses'] else ""
        _log(f"  [{i+1}/{total}] → score={result['scores']['total']:.2f} "
             f"domain={result['scores']['domain_completeness']:.2f} "
             f"fusion={result['scores']['fusion_quality']:.2f} "
             f"({result['duration_sec']}s, exit={exit_code}){miss_str}")

    config_elapsed = time.time() - config_start
    _log(f"  本配置总耗时: {config_elapsed:.1f}s")
    return results


def compute_summary(results: list[dict]) -> dict:
    scores = [r["scores"]["total"] for r in results]
    domain_comp = [r["scores"]["domain_completeness"] for r in results]
    fusion_q = [r["scores"]["fusion_quality"] for r in results]
    durations = [r["duration_sec"] for r in results]
    return {
        "avg_score": round(sum(scores) / len(scores), 3) if scores else 0,
        "avg_domain_completeness": round(sum(domain_comp) / len(domain_comp), 3) if domain_comp else 0,
        "avg_fusion_quality": round(sum(fusion_q) / len(fusion_q), 3) if fusion_q else 0,
        "pass_rate": round(sum(1 for s in scores if s >= 0.6) / len(scores), 3) if scores else 0,
        "total_duration": round(sum(durations), 1),
    }


def run_config(config_name: str, timeout: int = 600) -> dict:
    """执行单个消融配置"""
    label = CONFIG_LABELS.get(config_name, config_name)
    _log(f"\n{'='*60}")
    _log(f"配置: {config_name} ({label})")
    _log(f"{'='*60}")

    # 恢复原始文件
    restore_originals()

    # 应用 mutation
    applier = CONFIG_MAP.get(config_name)
    if applier:
        applier()
        _log(f"  已应用 mutation: {config_name}")
        _log(f"  fusion hash={_file_hash(FUSION_PY)}, planner hash={_file_hash(PLANNER_PY)}")
    else:
        _log(f"  使用完整系统（无 mutation）")

    # 记录 mutation 后源文件关键片段
    if config_name == "no-dual-graph":
        fusion_src = PLANNER_PY.read_text()
        m = re.search(r'BUSINESS_DEPENDENCIES\s*=\s*\{[^}]+\}', fusion_src, re.DOTALL)
        if m:
            _log(f"  BUSINESS_DEPENDENCIES 已变为: {m.group()[:200]}")
    elif config_name == "no-fusion":
        fusion_src = FUSION_PY.read_text()
        has_ablation = "Ablation: 不做关联分析" in fusion_src and "Ablation: 直接拼接不做融合" in fusion_src
        _log(f"  correlate/fuse ablation 注入: {'OK' if has_ablation else 'FAIL'}")

    config_start = time.time()

    # 执行测试
    results = run_all_tests(timeout)
    summary = compute_summary(results)

    elapsed = time.time() - config_start
    _log(f"  结果: avg_score={summary['avg_score']:.3f}, "
         f"domain={summary['avg_domain_completeness']:.3f}, "
         f"fusion={summary['avg_fusion_quality']:.3f}, "
         f"pass_rate={summary['pass_rate']:.1%}, "
         f"elapsed={elapsed:.0f}s")

    return {
        "config": config_name,
        "label": label,
        "summary": summary,
        "results": results,
        "config_duration_sec": round(elapsed, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="消融实验")
    parser.add_argument("--config", choices=list(CONFIG_MAP.keys()), help="指定单个配置")
    parser.add_argument("--all", action="store_true", help="跑全部6组配置")
    parser.add_argument("--timeout", type=int, default=600, help="单题超时秒数")
    args = parser.parse_args()

    if not args.config and not args.all:
        parser.error("请指定 --config <name> 或 --all")

    _log("=" * 60)
    _log("消融实验开始")
    _log(f"配置数: {'6 (全部)' if args.all else '1 (' + args.config + ')'}")
    _log(f"每配置测试题数: {len(FUSION_TESTS)}")
    _log(f"单题超时: {args.timeout}s")
    _log(f"预计总耗时: {len(FUSION_TESTS) * args.timeout * (6 if args.all else 1) / 60:.0f} 分钟（最坏情况）")
    _log("=" * 60)

    overall_start = time.time()

    # 备份原始文件
    backup_originals()

    configs = list(CONFIG_MAP.keys()) if args.all else [args.config]
    all_data = []

    try:
        for idx, config in enumerate(configs):
            _log(f"\n>>> 进度: [{idx+1}/{len(configs)}] 开始配置 {config}")
            data = run_config(config, args.timeout)
            all_data.append(data)

        # 恢复原始文件
        restore_originals()

        # 生成报告
        output_dir = Path("/opt/git/hermes-agent/skills/water-resources/reports/ablation")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"ablation_{timestamp}.json"

        report_data = {
            "timestamp": timestamp,
            "total_elapsed_sec": round(time.time() - overall_start, 1),
            "timeout_per_test": args.timeout,
            "configs": all_data,
        }

        with open(report_path, "w") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # 打印对比表
        _log(f"\n{'='*70}")
        _log("消融实验结果对比")
        _log(f"{'='*70}")
        _log(f"{'配置':<20} {'平均分':>8} {'域完整':>8} {'融合质量':>8} {'通过率':>8} {'耗时':>8}")
        _log("-" * 70)
        for d in all_data:
            s = d["summary"]
            _log(f"{d['config']:<20} {s['avg_score']:>8.3f} {s['avg_domain_completeness']:>8.3f} "
                  f"{s['avg_fusion_quality']:>8.3f} {s['pass_rate']:>8.1%} {s['total_duration']:>7.1f}s")

        # 计算各创新点贡献
        if len(all_data) > 1:
            full = next(d for d in all_data if d["config"] == "full")
            _log(f"\n各创新点贡献（Full - Ablated）:")
            _log(f"{'创新点':<35} {'分数差异':>10} {'融合质量差异':>12}")
            _log("-" * 60)
            labels = {
                "no-dual-graph": "双图分离(创新点2)",
                "no-adaptive": "自适应时间粒度(创新点4)",
                "no-normalize": "站名归一化(创新点4)",
                "no-conflict": "冲突检测与消解(创新点5)",
                "no-fusion": "三维关联+智能融合(创新点3+4+5)",
            }
            for d in all_data:
                if d["config"] != "full":
                    label = labels.get(d["config"], d["config"])
                    score_diff = full["summary"]["avg_score"] - d["summary"]["avg_score"]
                    fusion_diff = full["summary"]["avg_fusion_quality"] - d["summary"]["avg_fusion_quality"]
                    sign_s = "+" if score_diff > 0 else ""
                    sign_f = "+" if fusion_diff > 0 else ""
                    _log(f"  {label:<33} {sign_s}{score_diff:>8.3f} {sign_f}{fusion_diff:>10.3f}")

        total_elapsed = time.time() - overall_start
        _log(f"\n总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
        _log(f"报告: {report_path}")

    except Exception as e:
        restore_originals()
        _log(f"\n[ERROR] {e}")
        import traceback
        _log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()

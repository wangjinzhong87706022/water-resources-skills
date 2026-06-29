#!/usr/bin/env python3
"""
water-fusion 跨域融合 Autoresearch 优化脚本

用法:
  # 建立基线
  python autoresearch-fusion.py --phase baseline

  # 验证 mutation 效果
  python autoresearch-fusion.py --phase verify --mutation "描述变更内容"

流程:
  1. baseline: 执行全部跨域测试题，记录基线分数
  2. (手动修改 water-fusion/SKILL.md 或 fusion.py)
  3. verify: 重新执行测试，与基线对比
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 跨域测试题定义
FUSION_TESTS = [
    {
        "id": "F1",
        "question": "综合查询古运河水位和降雨情况",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨"],
        "fusion_type": "时间对齐",
    },
    {
        "id": "F2",
        "question": "分析最近降雨对古运河水位的影响",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨"],
        "fusion_type": "业务逻辑",
    },
    {
        "id": "F3",
        "question": "查询古运河实时水位，并判断是否超过警戒水位",
        "skills": "water-fusion",
        "expected_domains": ["水位", "警戒"],
        "fusion_type": "业务逻辑",
    },
    {
        "id": "F4",
        "question": "查询瘦西湖最新水质数据，判断水质等级",
        "skills": "water-fusion",
        "expected_domains": ["水质", "等级"],
        "fusion_type": "业务逻辑",
    },
    {
        "id": "F5",
        "question": "查询古运河沿线水位及附近闸站运行情况",
        "skills": "water-fusion",
        "expected_domains": ["水位", "闸", "泵"],
        "fusion_type": "空间对齐",
    },
    {
        "id": "F6",
        "question": "扬州市防洪形势综合分析：当前水位、降雨、闸泵运行和预警状态",
        "skills": "water-fusion",
        "expected_domains": ["水位", "降雨", "闸", "泵", "预警"],
        "fusion_type": "混合",
    },
    {
        "id": "F7",
        "question": "2024年8月扬州城区降雨量最大的那天，各重点河道水位是否超警戒",
        "skills": "water-fusion",
        "expected_domains": ["降雨", "水位", "警戒"],
        "fusion_type": "时间对齐",
    },
    {
        "id": "F8",
        "question": "查询古运河最新水位",
        "skills": "water-situation",
        "expected_domains": ["水位"],
        "fusion_type": "单域（不应触发融合）",
    },
]

BASELINE_FILE = Path(__file__).resolve().parent.parent / "reports" / "autoresearch-fusion" / "baseline.json"


def run_hermes(prompt: str, skill: str, timeout: int = 600) -> tuple[str, float]:
    """执行 hermes -z 并返回 (response, duration)"""
    cmd = ["hermes", "-z", prompt, "-s", skill]
    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "HERMES_YOLO_MODE": "1", "HERMES_ACCEPT_HOOKS": "1"},
        )
        duration = time.time() - start
        response = result.stdout.strip()
        if not response and result.stderr:
            response = f"[STDERR]: {result.stderr.strip()}"
        return response, duration
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s]", time.time() - start
    except Exception as e:
        return f"[ERROR]: {e}", time.time() - start


def evaluate_response(test: dict, response: str, duration: float) -> dict:
    """评估单个跨域查询的回答质量"""
    scores = {}

    # 维度1: 回答有效性 (0/0.5/1.0)
    if not response or response.startswith("[STDERR]") or response.startswith("[ERROR") or response.startswith("[TIMEOUT"):
        scores["valid_response"] = 0.0
    elif len(response) > 100:
        scores["valid_response"] = 1.0
    else:
        scores["valid_response"] = 0.5

    # 维度2: 领域数据完整性 — 检查是否包含所有预期域的数据
    expected = test["expected_domains"]
    domain_hits = [kw for kw in expected if kw in response]
    domain_ratio = len(domain_hits) / len(expected) if expected else 0
    scores["domain_completeness"] = round(domain_ratio, 2)
    scores["domain_hits"] = domain_hits
    scores["domain_misses"] = [kw for kw in expected if kw not in response]

    # 维度3: 融合分析质量 — 检查是否包含跨域关联分析
    fusion_keywords = [
        "影响", "关联", "因果", "相关", "导致", "对比", "综合", "分析",
        "上涨", "下降", "变化", "趋势", "响应", "涨幅", "回落",
        "融合策略", "对齐", "空间对齐", "时间对齐",
    ]
    fusion_hits = [kw for kw in fusion_keywords if kw in response]
    # 多域查询需要有融合分析，单域查询不需要
    if len(test["expected_domains"]) > 1:
        scores["fusion_quality"] = min(1.0, len(fusion_hits) / 3.0)
    else:
        scores["fusion_quality"] = 1.0  # 单域不检查融合
    scores["fusion_keywords_found"] = fusion_hits

    # 维度4: 数值数据
    numbers = re.findall(r"\d+\.?\d*", response)
    scores["has_numeric"] = 1.0 if len(numbers) >= 3 else 0.5 if len(numbers) >= 1 else 0.0

    # 加权总分: 有效性(15%) + 域完整性(35%) + 融合质量(30%) + 数值(20%)
    total = (
        scores["valid_response"] * 0.15
        + scores["domain_completeness"] * 0.35
        + scores["fusion_quality"] * 0.30
        + scores["has_numeric"] * 0.20
    )
    scores["total"] = round(total, 2)

    return {
        "id": test["id"],
        "question": test["question"],
        "skill": test["skills"],
        "fusion_type": test["fusion_type"],
        "expected_domains": test["expected_domains"],
        "duration_sec": round(duration, 1),
        "response_preview": response[:200] + "..." if len(response) > 200 else response,
        "response_length": len(response),
        "scores": scores,
    }


def run_all_tests(timeout: int = 600) -> list[dict]:
    """执行所有跨域测试"""
    results = []
    total = len(FUSION_TESTS)
    for i, test in enumerate(FUSION_TESTS):
        print(f"\n[{i+1}/{total}] {test['id']}: {test['question'][:60]}")
        print(f"  skill={test['skills']}, 期望域={test['expected_domains']}, 融合类型={test['fusion_type']}")
        response, duration = run_hermes(test["question"], test["skills"], timeout)
        result = evaluate_response(test, response, duration)
        results.append(result)
        print(f"  → 总分={result['scores']['total']:.2f} | "
              f"域完整={result['scores']['domain_completeness']:.2f} | "
              f"融合={result['scores']['fusion_quality']:.2f} | "
              f"耗时={result['duration_sec']}s")
        if result["scores"]["domain_misses"]:
            print(f"  ⚠ 缺失域: {result['scores']['domain_misses']}")
    return results


def compute_summary(results: list[dict]) -> dict:
    """计算汇总统计"""
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
        "count": len(results),
    }


def save_results(results: list[dict], phase: str, mutation: str = ""):
    """保存结果"""
    output_dir = Path(__file__).resolve().parent.parent / "reports" / "autoresearch-fusion"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{phase}_{timestamp}.json"

    data = {
        "phase": phase,
        "mutation": mutation,
        "timestamp": timestamp,
        "summary": compute_summary(results),
        "results": results,
    }

    filepath = output_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {filepath}")
    return filepath


def compare_with_baseline(verify_results: list[dict]):
    """与基线对比"""
    if not BASELINE_FILE.exists():
        print("[WARN] 基线文件不存在，无法对比")
        return

    with open(BASELINE_FILE, "r") as f:
        baseline = json.load(f)

    base_summary = baseline["summary"]
    verify_summary = compute_summary(verify_results)

    print("\n" + "=" * 60)
    print("基线 vs 当前 对比:")
    print("=" * 60)
    print(f"{'指标':<25} {'基线':>10} {'当前':>10} {'变化':>10}")
    print("-" * 60)

    for key in ["avg_score", "avg_domain_completeness", "avg_fusion_quality", "pass_rate"]:
        base_val = base_summary.get(key, 0)
        veri_val = verify_summary.get(key, 0)
        diff = veri_val - base_val
        sign = "+" if diff > 0 else ""
        print(f"  {key:<23} {base_val:>10.3f} {veri_val:>10.3f} {sign}{diff:>9.3f}")

    base_dur = base_summary.get("total_duration", 0)
    veri_dur = verify_summary.get("total_duration", 0)
    dur_diff = veri_dur - base_dur
    print(f"  {'total_duration':<23} {base_dur:>10.1f}s {veri_dur:>10.1f}s {dur_diff:>+9.1f}s")

    # 逐题对比
    print("\n逐题对比:")
    base_by_id = {r["id"]: r for r in baseline["results"]}
    improved = 0
    regressed = 0
    for vr in verify_results:
        fid = vr["id"]
        if fid in base_by_id:
            base_score = base_by_id[fid]["scores"]["total"]
            veri_score = vr["scores"]["total"]
            diff = veri_score - base_score
            sign = "+" if diff > 0 else ""
            status = "✓" if diff >= 0 else "✗ REGRESS"
            if diff > 0:
                improved += 1
            elif diff < 0:
                regressed += 1
            print(f"  {fid}: {base_score:.2f} → {veri_score:.2f} ({sign}{diff:.2f}) {status}")
        else:
            print(f"  {fid}: 新题 {vr['scores']['total']:.2f}")

    print(f"\n改善: {improved} 题 | 退步: {regressed} 题")

    if regressed == 0 and improved > 0:
        print("→ 判定: KEEP (有改善无退步)")
    elif regressed > 0:
        print("→ 判定: DISCARD (存在退步)")
    else:
        print("→ 判定: NEUTRAL (无变化)")


def main():
    parser = argparse.ArgumentParser(description="water-fusion Autoresearch 优化")
    parser.add_argument("--phase", choices=["baseline", "verify"], required=True,
                        help="baseline=建立基线, verify=验证 mutation")
    parser.add_argument("--mutation", default="", help="mutation 描述（verify 阶段使用）")
    parser.add_argument("--timeout", type=int, default=600, help="单题超时秒数")
    args = parser.parse_args()

    print(f"Phase: {args.phase}")
    if args.mutation:
        print(f"Mutation: {args.mutation}")
    print(f"测试题数: {len(FUSION_TESTS)}")
    print(f"超时: {args.timeout}s/题")

    results = run_all_tests(args.timeout)
    summary = compute_summary(results)

    print("\n" + "=" * 60)
    print("汇总:")
    print(f"  平均分: {summary['avg_score']:.3f}")
    print(f"  域完整性: {summary['avg_domain_completeness']:.3f}")
    print(f"  融合质量: {summary['avg_fusion_quality']:.3f}")
    print(f"  通过率: {summary['pass_rate']:.1%}")
    print(f"  总耗时: {summary['total_duration']}s")

    filepath = save_results(results, args.phase, args.mutation)

    if args.phase == "baseline":
        # 同时保存为基线文件
        baseline_dir = BASELINE_FILE.parent
        baseline_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "phase": "baseline",
            "mutation": "",
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "summary": summary,
            "results": results,
        }
        with open(BASELINE_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"基线已保存: {BASELINE_FILE}")

    elif args.phase == "verify":
        compare_with_baseline(results)


if __name__ == "__main__":
    main()

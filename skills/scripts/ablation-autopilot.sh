#!/bin/bash
# 消融实验 + 专利文档更新 — 全自动无人值守脚本
#
# 启动方式（断开shell也不会中断）:
#   nohup bash /opt/git/hermes-agent/skills/water-resources/scripts/ablation-autopilot.sh > /tmp/ablation-run.log 2>&1 &
#
# 查看进度:
#   tail -f /tmp/ablation-run.log

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
LOG="/tmp/ablation-run.log"
PATENT_FILE="/home/scada/dataagent/patent/patent-application-v2.md"
REPORT_DIR="$SKILL_ROOT/reports/ablation"

echo "========================================" | tee -a "$LOG"
echo "消融实验自动执行 — $(date)" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

# ── 第1步: 运行消融实验 ─────────────────────────────────────
echo "" | tee -a "$LOG"
echo "[Step 1/3] 运行消融实验 (6组 × 8题, 预计2-3小时)..." | tee -a "$LOG"
echo "开始时间: $(date)" | tee -a "$LOG"

cd "$SKILL_ROOT"
PYTHONUNBUFFERED=1 python3 -u scripts/ablation_fusion.py --all --timeout 600 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "消融实验完成: $(date)" | tee -a "$LOG"

# ── 第2步: 解析最新结果 ─────────────────────────────────────
echo "" | tee -a "$LOG"
echo "[Step 2/3] 解析实验结果..." | tee -a "$LOG"

# 找到最新的 ablation JSON 报告
LATEST_JSON=$(ls -t "$REPORT_DIR"/ablation_*.json 2>/dev/null | head -1)

if [ -z "$LATEST_JSON" ]; then
    echo "[ERROR] 未找到消融实验结果文件" | tee -a "$LOG"
    exit 1
fi

echo "结果文件: $LATEST_JSON" | tee -a "$LOG"

# 用 Python 解析结果并生成 Markdown 表格
python3 -u << 'PYEOF' | tee -a "$LOG"
import json
import sys
import glob
import os

files = sorted(glob.glob("/opt/git/hermes-agent/skills/water-resources/reports/ablation/ablation_*.json"))
if not files:
    print("[ERROR] No ablation results found")
    sys.exit(1)

latest = files[-1]
print(f"Reading: {latest}")

with open(latest) as f:
    report = json.load(f)

# 兼容新版（configs字段）和旧版（直接列表）
if isinstance(report, list):
    data = report
    total_elapsed = None
    timestamp = ""
else:
    data = report["configs"]
    total_elapsed = report.get("total_elapsed_sec")
    timestamp = report.get("timestamp", "")

tmp = "/tmp/ablation-results.md"
with open(tmp, "w") as f:
    f.write("## 实验验证 — 消融实验\n\n")
    f.write("### 实验设计\n\n")
    f.write("通过逐一移除各创新点，测量其对系统性能的独立贡献。\n\n")
    f.write("| 配置 | 说明 | 移除的创新点 |\n")
    f.write("|------|------|-------------|\n")
    f.write("| Full | 完整系统 | — |\n")
    f.write("| no-dual-graph | 因果关联→执行依赖（单一依赖图） | 创新点2：双图分离 |\n")
    f.write("| no-adaptive | 固定DAY粒度 | 创新点4：自适应时间粒度推断 |\n")
    f.write("| no-normalize | 不做站名后缀去除 | 创新点4：站名归一化 |\n")
    f.write("| no-conflict | 跳过冲突检测和消解 | 创新点5：冲突检测与消解 |\n")
    f.write("| no-fusion | 简单拼接，不做关联分析和融合 | 创新点3+4+5：智能融合 |\n\n")

    f.write("### 实验结果\n\n")
    f.write("| 配置 | 平均分 | 域完整性 | 融合质量 | 通过率 | 耗时(s) |\n")
    f.write("|------|--------|---------|---------|--------|--------|\n")

    for d in data:
        s = d["summary"]
        f.write(f"| {d['config']} | {s['avg_score']:.3f} | {s['avg_domain_completeness']:.3f} "
                f"| {s['avg_fusion_quality']:.3f} | {s['pass_rate']:.1%} | {s['total_duration']:.0f} |\n")

    full = next(d for d in data if d["config"] == "full")
    f.write("\n### 各创新点贡献度\n\n")
    f.write("贡献度 = Full系统分数 - 移除该创新点后的分数\n\n")
    f.write("| 创新点 | 分数差异 | 融合质量差异 | 说明 |\n")
    f.write("|--------|---------|-------------|------|\n")

    labels = {
        "no-dual-graph": ("双图分离策略", "将因果关联作为执行依赖，导致本可并行的Skill被强制串行"),
        "no-adaptive": ("自适应时间粒度推断", "固定DAY粒度无法处理不同采样频率的数据源"),
        "no-normalize": ("站名归一化方法", "不同子系统的站名后缀导致空间关联失败"),
        "no-conflict": ("领域阈值冲突检测", "跳过冲突检测可能导致数据不一致"),
        "no-fusion": ("三维关联+智能融合", "简单拼接无法识别跨域数据关联"),
    }

    for d in data:
        if d["config"] != "full":
            label, desc = labels.get(d["config"], (d["config"], ""))
            score_diff = full["summary"]["avg_score"] - d["summary"]["avg_score"]
            fusion_diff = full["summary"]["avg_fusion_quality"] - d["summary"]["avg_fusion_quality"]
            f.write(f"| {label} | {score_diff:+.3f} | {fusion_diff:+.3f} | {desc} |\n")

    f.write(f"\n### 实验结论\n\n")

    contributions = []
    for d in data:
        if d["config"] != "full":
            diff = full["summary"]["avg_score"] - d["summary"]["avg_score"]
            contributions.append((d["config"], diff))
    contributions.sort(key=lambda x: -x[1])

    for i, (cfg, diff) in enumerate(contributions, 1):
        label = labels.get(cfg, (cfg, ""))[0]
        if i == 1:
            f.write(f"{i}. **{label}贡献最大**：移除后分数下降 {diff:+.3f}，验证了该创新点的核心价值。\n")
        else:
            f.write(f"{i}. **{label}**: 贡献 {diff:+.3f} 分。\n")

    elapsed_str = f"，总耗时 {total_elapsed:.0f}s" if total_elapsed else ""
    f.write(f"\n---\n*实验时间: {timestamp}{elapsed_str}*\n")

print(f"\nResults written to: {tmp}")
PYEOF

echo "" | tee -a "$LOG"

# ── 第3步: 更新专利文档 ─────────────────────────────────────
echo "[Step 3/3] 更新专利文档..." | tee -a "$LOG"

if [ -f "/tmp/ablation-results.md" ] && [ -f "$PATENT_FILE" ]; then
    python3 -u << 'PYEOF2'
import re

patent_file = "/home/scada/dataagent/patent/patent-application-v2.md"
results_file = "/tmp/ablation-results.md"

with open(patent_file, "r") as f:
    patent = f.read()

with open(results_file, "r") as f:
    ablation_section = f.read()

marker = "## 实验验证"
if marker in patent:
    start = patent.index(marker)
    next_section = patent.find("\n## ", start + 10)
    if next_section == -1:
        next_section = len(patent)
    new_patent = patent[:start] + ablation_section.rstrip() + "\n\n" + patent[next_section:]
    with open(patent_file, "w") as f:
        f.write(new_patent)
    print(f"已更新专利文档: {patent_file}")
else:
    with open(patent_file, "a") as f:
        f.write("\n\n" + ablation_section)
    print(f"已追加到专利文档: {patent_file}")
PYEOF2
else
    echo "[WARN] 缺少文件，跳过专利更新" | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "全部完成: $(date)" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "日志: $LOG" | tee -a "$LOG"
echo "结果: $REPORT_DIR/" | tee -a "$LOG"
echo "专利: $PATENT_FILE" | tee -a "$LOG"

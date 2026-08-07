#!/bin/bash
# Eval 基线监控脚本
# 用法: bash scripts/monitor_eval.sh

echo "=== Eval 基线监控 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查进程
if ps aux | grep -v grep | grep evaluate_skills.py > /dev/null; then
    PID=$(ps aux | grep -v grep | grep evaluate_skills.py | awk '{print $2}')
    echo "✅ Eval 进程运行中 (PID: $PID)"
    echo "   启动时间: $(ps -p $PID -o lstart= 2>/dev/null || echo '未知')"
    echo "   CPU 占用: $(ps -p $PID -o %cpu= 2>/dev/null || echo '未知')%"
    echo "   内存占用: $(ps -p $PID -o rss= 2>/dev/null || echo '未知') KB"
else
    echo "❌ Eval 进程未运行"
fi

echo ""

# 检查输出日志
LOG="/tmp/claude-0/-opt-git-water-resources-skills/bb4d1336-9d10-4238-aeb5-a17a768e1a31/tasks/b39bcda3x.output"
if [ -f "$LOG" ]; then
    LINES=$(wc -l < "$LOG")
    echo "📊 输出日志: $LINES 行"
    if [ "$LINES" -gt 0 ]; then
        echo ""
        echo "=== 最新 10 行 ==="
        tail -10 "$LOG"
    fi
else
    echo "📊 输出日志: 文件不存在"
fi

echo ""

# 检查报告目录
REPORT_DIR="/opt/git/water-resources-skills/skills/reports/eval_baseline_20260728"
if [ -d "$REPORT_DIR" ]; then
    echo "📁 报告目录: 已创建"
    ls -lh "$REPORT_DIR" 2>/dev/null | tail -5
else
    echo "📁 报告目录: 尚未创建（eval 未完成）"
fi

echo ""
echo "=== 监控完成 ==="

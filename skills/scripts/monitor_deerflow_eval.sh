#!/bin/bash
# DeerFlow Eval 监控脚本

LOG="/tmp/deerflow_eval.log"
PID=3111287

echo "=== DeerFlow Eval 监控 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查进程
if ps -p $PID > /dev/null 2>&1; then
    echo "✅ Eval 进程运行中 (PID: $PID)"
    echo "   运行时间: $(ps -p $PID -o etime= 2>/dev/null || echo '未知')"
else
    echo "❌ Eval 进程已结束"
fi

echo ""

# 查看日志
if [ -f "$LOG" ]; then
    LINES=$(wc -l < "$LOG")
    echo "📊 日志: $LINES 行"
    if [ "$LINES" -gt 0 ]; then
        echo ""
        echo "=== 最新 15 行 ==="
        tail -15 "$LOG"
    fi
else
    echo "📊 日志: 文件不存在"
fi

echo ""

# 检查报告
REPORT_DIR=$(ls -td /opt/git/water-resources-skills/skills/reports/deerflow_baseline_water_situation_* 2>/dev/null | head -1)
if [ -n "$REPORT_DIR" ]; then
    echo "📁 报告目录: $REPORT_DIR"
    ls -lh "$REPORT_DIR" 2>/dev/null | tail -5
else
    echo "📁 报告: 尚未生成"
fi

echo ""
echo "=== 监控完成 ==="

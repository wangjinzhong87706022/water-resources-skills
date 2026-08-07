#!/bin/bash
# 全量 98 题 Eval 监控

PID=3208308
LOG="/tmp/deerflow_98_full.log"
CHECK_INTERVAL=30  # 每 30 秒检查一次

echo "========================================"
echo "🦌 DeerFlow 全量 98 题 Eval 监控"
echo "========================================"
echo "PID: $PID"
echo "日志: $LOG"
echo "检查间隔: ${CHECK_INTERVAL}秒"
echo ""

while ps -p $PID > /dev/null 2>&1; do
    clear
    echo "========================================"
    echo "🦌 DeerFlow 全量 98 题 Eval 监控"
    echo "========================================"
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 进程状态
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ 进程运行中 (PID: $PID)"
        ps -p $PID -o etime=,%cpu=,%mem= 2>/dev/null | awk '{print "   运行时间: "$1" | CPU: "$2"% | 内存: "$3"%"}'
    else
        echo "❌ 进程已结束"
    fi

    echo ""

    # 进度统计
    if [ -f "$LOG" ]; then
        LINES=$(wc -l < "$LOG")
        COMPLETED=$(grep -c "^\[.*\] Q.*→" "$LOG" 2>/dev/null || echo "0")
        LAST_Q=$(grep "^\[.*\] Q" "$LOG" 2>/dev/null | tail -1 | grep -oP 'Q\[\d+' | sed 's/Q\[//')

        echo "📊 进度统计:"
        echo "   完成: $COMPLETED / 98 题"
        echo "   当前: $LAST_Q"

        if [ "$COMPLETED" -gt 0 ]; then
            SCORES=$(grep "^\[.*\] Q.*→" "$LOG" | grep -oP '总分=\K[0-9.]+' | awk '{sum+=$1} END {if(NR>0) print sum/NR; else print 0}')
            echo "   平均分: $(echo $SCORES | awk '{printf "%.2f", $1}')"
        fi
    fi

    echo ""

    # 最新 10 行日志
    if [ -f "$LOG" ]; then
        echo "=== 最新 10 行 ==="
        tail -10 "$LOG"
    fi

    echo ""
    echo "下次检查: ${CHECK_INTERVAL}秒后..."
    sleep $CHECK_INTERVAL
done

# 进程结束后生成最终报告
echo ""
echo "========================================"
echo "✅ Eval 完成"
echo "========================================"
echo ""

# 查找报告目录
REPORT_DIR=$(ls -td /opt/git/water-resources-skills/skills/reports/deerflow_baseline_98_full_* 2>/dev/null | head -1)
if [ -n "$REPORT_DIR" ]; then
    echo "📁 报告目录: $REPORT_DIR"
    ls -lh "$REPORT_DIR" 2>/dev/null

    # 读取 Markdown 报告
    MD_FILE=$(ls -t "$REPORT_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$MD_FILE" ]; then
        echo ""
        echo "=== 最终报告 ==="
        cat "$MD_FILE"
    fi
else
    echo "⚠️  报告目录未找到"
fi

echo ""
echo "========================================"
echo "监控结束"
echo "========================================"

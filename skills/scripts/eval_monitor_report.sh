#!/bin/bash
# DeerFlow Gateway 评测自动监控脚本（每5分钟执行一次）

LOG_FILE="/tmp/claude-0/-opt-git-water-resources-skills/775a4877-2ab9-45cc-8341-140a2dd8fbdf/tasks/bfrv6dp5y.output"
REPORT_DIR="/opt/git/water-resources-skills/skills/reports/eval_gateway_full"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "========================================"
echo "DeerFlow Gateway 评测监控报告"
echo "时间: $TIMESTAMP"
echo "========================================"
echo ""

# 检查进程是否还在运行
PID=$(ps aux | grep "evaluate_deerflow_gateway.py --all-skills" | grep -v grep | awk '{print $2}')
if [ -z "$PID" ]; then
    echo "⚠️  评测进程已结束"
    echo ""
    echo "最新报告："
    ls -lht "$REPORT_DIR"/ 2>/dev/null | head -5
    exit 1
fi

echo "✅ 评测进程运行中 (PID: $PID)"
echo ""

# 统计已完成题目
if [ -f "$LOG_FILE" ]; then
    COMPLETED=$(grep -c "^  ✓" "$LOG_FILE" 2>/dev/null || echo "0")
    TOTAL=98
    PERCENT=$(awk "BEGIN {printf \"%.1f\", $COMPLETED/$TOTAL*100}")

    echo "📊 完成进度: $COMPLETED / $TOTAL ($PERCENT%)"
    echo ""

    # 显示最近5条完成记录
    echo "📝 最近完成的题目："
    grep "^  ✓" "$LOG_FILE" | tail -5 | while read line; do
        echo "  $line"
    done
    echo ""

    # 计算平均分
    SCORES=$(grep "^  ✓" "$LOG_FILE" | awk '{print $NF}' | sed 's/score=//')
    if [ -n "$SCORES" ]; then
        AVG_SCORE=$(echo "$SCORES" | awk '{sum+=$1; count++} END {printf "%.3f", sum/count}')
        echo "📈 平均得分: $AVG_SCORE"
        echo ""

        # 统计通过率（≥0.6）
        PASS_COUNT=$(echo "$SCORES" | awk '$1 >= 0.6 {count++} END {print count+0}')
        PASS_RATE=$(awk "BEGIN {printf \"%.1f\", $PASS_COUNT/$COMPLETED*100}")
        echo "✅ 通过率(≥0.6): $PASS_COUNT/$COMPLETED ($PASS_RATE%)"
        echo ""
    fi

    # 显示当前正在运行的题目
    CURRENT=$(grep -A1 "^\[" "$LOG_FILE" | tail -1 | grep "^\[" | head -1)
    if [ -n "$CURRENT" ]; then
        echo "⏳ 当前运行: $CURRENT"
        echo ""
    fi

    # 估算剩余时间
    if [ "$COMPLETED" -gt 0 ]; then
        # 获取最近3题的耗时
        RECENT_TIMES=$(grep "^  ✓" "$LOG_FILE" | tail -3 | awk '{print $2}' | sed 's/s//')
        if [ -n "$RECENT_TIMES" ]; then
            AVG_TIME=$(echo "$RECENT_TIMES" | awk '{sum+=$1; count++} END {printf "%.0f", sum/count}')
            REMAINING=$((TOTAL - COMPLETED))
            EST_SECONDS=$((AVG_TIME * REMAINING))
            EST_HOURS=$(awk "BEGIN {printf \"%.1f\", $EST_SECONDS/3600}")

            echo "⏱️  时间估算:"
            echo "  最近平均: ${AVG_TIME}秒/题"
            echo "  剩余题目: $REMAINING"
            echo "  预计剩余: ${EST_HOURS} 小时"
            echo ""
        fi
    fi
fi

echo "========================================"
echo ""

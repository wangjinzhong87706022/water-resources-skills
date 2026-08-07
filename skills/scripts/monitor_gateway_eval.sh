#!/bin/bash
# DeerFlow Gateway 评测监控脚本

echo "========================================"
echo "DeerFlow Gateway 评测监控"
echo "========================================"
echo ""

# 检查进程是否还在运行
PID=$(ps aux | grep "evaluate_deerflow_gateway.py --all-skills" | grep -v grep | awk '{print $2}')
if [ -z "$PID" ]; then
    echo "⚠️  评测进程未运行"
    echo ""
    echo "最新报告："
    ls -lht /opt/git/water-resources-skills/skills/reports/eval_gateway_full/ 2>/dev/null | head -5
    exit 1
fi

echo "✅ 评测进程正在运行 (PID: $PID)"
echo ""

# 显示最新输出
LOG_FILE="/tmp/claude-0/-opt-git-water-resources-skills/775a4877-2ab9-45cc-8341-140a2dd8fbdf/tasks/bfrv6dp5y.output"
if [ -f "$LOG_FILE" ]; then
    echo "📊 最新进度："
    tail -20 "$LOG_FILE"
    echo ""

    # 统计完成的题数
    COMPLETED=$(grep -c "^  ✓" "$LOG_FILE" 2>/dev/null || echo "0")
    TOTAL=98
    echo "完成进度: $COMPLETED / $TOTAL ($(awk "BEGIN {printf \"%.1f\", $COMPLETED/$TOTAL*100}")%)"
else
    echo "⚠️  日志文件未找到"
fi

echo ""
echo "报告目录："
ls -lht /opt/git/water-resources-skills/skills/reports/eval_gateway_full/ 2>/dev/null | head -3

#!/bin/bash
# 快速查看最新监控报告

echo "========================================"
echo "📊 最新监控报告"
echo "========================================"
echo ""

if [ -f /tmp/deerflow_eval_monitor.log ]; then
    # 提取最后一次监控数据
    LAST_REPORT=$(grep -A20 "监控检查" /tmp/deerflow_eval_monitor.log | tail -20)

    if [ -n "$LAST_REPORT" ]; then
        echo "$LAST_REPORT"
    else
        echo "等待第一次监控数据..."
    fi
else
    echo "监控日志文件未创建"
fi

echo ""
echo "========================================"
echo "监控命令："
echo "  查看最新报告: tail -50 /tmp/deerflow_eval_monitor.log"
echo "  实时监控: watch -n 30 'tail -50 /tmp/deerflow_eval_monitor.log'"
echo "  查看评测输出: tail -50 /tmp/claude-0/-opt-git-water-resources-skills/775a4877-2ab9-45cc-8341-140a2dd8fbdf/tasks/bfrv6dp5y.output"
echo "========================================"

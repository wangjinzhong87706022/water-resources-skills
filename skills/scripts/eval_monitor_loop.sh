#!/bin/bash
# DeerFlow Gateway 评测自动监控（每5分钟）

LOG_FILE="/tmp/claude-0/-opt-git-water-resources-skills/775a4877-2ab9-45cc-8341-140a2dd8fbdf/tasks/bfrv6dp5y.output"
REPORT_SCRIPT="/opt/git/water-resources-skills/skills/scripts/eval_monitor_report.sh"

# 检查评测进程是否还在运行
PID=$(ps aux | grep "evaluate_deerflow_gateway.py --all-skills" | grep -v grep | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 评测进程已结束，停止监控" >> /tmp/deerflow_eval_monitor.log
    # 生成最终报告
    bash "$REPORT_SCRIPT" >> /tmp/deerflow_eval_monitor.log 2>&1
    exit 0
fi

# 执行监控报告
echo "" >> /tmp/deerflow_eval_monitor.log
echo ">>> $(date '+%Y-%m-%d %H:%M:%S') - 监控检查" >> /tmp/deerflow_eval_monitor.log
bash "$REPORT_SCRIPT" >> /tmp/deerflow_eval_monitor.log 2>&1

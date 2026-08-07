#!/bin/bash
# 评估任务监控脚本
# 用法: ./check_eval.sh

EVAL_DIR="/opt/git/water-resources-skills/skills/reports"
LOG_FILE=$(ls -t $EVAL_DIR/eval_full_*.log 2>/dev/null | head -1)
REPORT_DIR=$(ls -td $EVAL_DIR/eval_full_*/ 2>/dev/null | head -1)

echo "======================================"
echo "评估任务状态检查"
echo "======================================"
echo ""

# 检查进程
PID=$(ps aux | grep -E "python3.*evaluate_skills.py" | grep -v grep | awk '{print $2}')
if [ -z "$PID" ]; then
    echo "❌ 评估进程未运行"
else
    echo "✅ 评估进程正在运行 (PID: $PID)"
    echo "   启动时间: $(ps -p $PID -o lstart=)"
    echo "   运行时长: $(ps -p $PID -o etime=)"
fi
echo ""

# 检查日志
if [ -n "$LOG_FILE" ]; then
    echo "📋 日志文件: $LOG_FILE"
    echo "   大小: $(ls -lh $LOG_FILE | awk '{print $5}')"
    echo "   最后修改: $(stat -c %y $LOG_FILE | cut -d. -f1)"
    if [ -s "$LOG_FILE" ]; then
        echo ""
        echo "--- 最近日志内容 ---"
        tail -30 "$LOG_FILE"
        echo "---"
    else
        echo "   ⚠️  日志文件为空（Python缓冲或任务刚启动）"
    fi
else
    echo "❌ 未找到日志文件"
fi
echo ""

# 检查报告目录
if [ -n "$REPORT_DIR" ]; then
    echo "📊 最新报告目录: $REPORT_DIR"
    echo "   文件列表:"
    ls -lh "$REPORT_DIR" | tail -n +2 | awk '{print "   - "$9" ("$5")"}'
else
    echo "ℹ️  报告目录尚未创建（任务可能还在运行）"
fi
echo ""

# 检查之前完成的评估
echo "📈 历史评估记录:"
ls -lht $EVAL_DIR/eval_full_*/ 2>/dev/null | head -5 | tail -n +2 | awk '{print "   "$9" ("$6" "$7" "$8")"}'
echo ""

echo "======================================"
echo "提示: 使用 'tail -f $LOG_FILE' 实时查看日志"
echo "======================================"

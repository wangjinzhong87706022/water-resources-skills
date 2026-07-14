#!/bin/bash
#
# DeerFlow 启动脚本（修复版）
# 正确的启动方式: make dev（不是 make gateway）
#

set -e

DEERFLOW_DIR="/opt/git/deer-flow"
BACKEND_ENV="$DEERFLOW_DIR/backend/.env"

echo "========================================"
echo "启动 DeerFlow"
echo "========================================"
echo

# 检查 DeerFlow 目录
if [ ! -d "$DEERFLOW_DIR" ]; then
    echo "❌ DeerFlow 目录不存在: $DEERFLOW_DIR"
    exit 1
fi

cd "$DEERFLOW_DIR"

# 加载环境变量
echo "[1/3] 加载环境变量"
echo "----------------------------------------"
if [ -f "$BACKEND_ENV" ]; then
    echo "✅ 加载 backend/.env"
    # 过滤掉注释和空行，只导出有效变量
    set -a
    source <(grep -v '^#' "$BACKEND_ENV" | grep -v '^$')
    set +a
    echo "   WATER_RESOURCES_ROOT=$WATER_RESOURCES_ROOT"
    echo "   SL323_DB_HOST=$SL323_DB_HOST"
    echo "   SL323_DB_PORT=$SL323_DB_PORT"
else
    echo "⚠️  backend/.env 不存在"
    echo "   请先运行: bash /opt/git/water-resources-skills/deploy/set_deerflow_password.sh"
    exit 1
fi
echo

# 检查服务是否已在运行
echo "[2/3] 检查现有服务"
echo "----------------------------------------"
if ss -ltn "( sport = :8001 )" 2>/dev/null | grep -q .; then
    echo "⚠️  端口 8001 已被占用"
    echo "   停止现有服务..."
    make stop
    sleep 2
fi
echo "✅ 端口 8001 可用"
echo

# 启动 DeerFlow
echo "[3/3] 启动 DeerFlow (make dev)"
echo "----------------------------------------"
echo "命令: make dev"
echo "日志: /opt/git/deer-flow/logs/gateway.log"
echo

# 在后台启动并等待
nohup make dev > /tmp/deerflow-dev-start.log 2>&1 &
DEERFLOW_PID=$!

echo "PID: $DEERFLOW_PID"
echo "等待服务启动..."
sleep 10

# 检查是否启动成功
if ps -p $DEERFLOW_PID > /dev/null 2>&1; then
    echo "✅ DeerFlow 进程正在运行"

    # 检查端口
    if ss -ltn "( sport = :8001 )" 2>/dev/null | grep -q .; then
        echo "✅ Gateway 端口 8001 已监听"
    else
        echo "⚠️  Gateway 端口 8001 未就绪（可能还在启动）"
    fi

    # 检查环境变量
    if tr '\0' '\n' < /proc/$DEERFLOW_PID/environ 2>/dev/null | grep -q "WATER_RESOURCES_ROOT=/mnt/skills"; then
        echo "✅ WATER_RESOURCES_ROOT 已注入"
    else
        echo "⚠️  WATER_RESOURCES_ROOT 未注入到进程"
        echo "   当前进程环境变量:"
        tr '\0' '\n' < /proc/$DEERFLOW_PID/environ 2>/dev/null | grep -E "WATER|SL323" | sed 's/=.*/=***/'
    fi

    echo
    echo "========================================"
    echo "✅ DeerFlow 已启动"
    echo "========================================"
    echo
    echo "访问: http://localhost:2026"
    echo "测试: '古运河有哪些水位测站？'"
    echo
    echo "查看日志:"
    echo "  tail -f /opt/git/deer-flow/logs/gateway.log"
    echo "  tail -f /opt/git/deer-flow/logs/frontend.log"
    echo
    echo "停止服务:"
    echo "  cd /opt/git/deer-flow && make stop"
    echo

else
    echo "❌ DeerFlow 启动失败"
    echo "查看启动日志:"
    tail -30 /tmp/deerflow-dev-start.log
    echo
    echo "尝试手动启动查看详细错误:"
    echo "  cd /opt/git/deer-flow"
    echo "  make dev"
    exit 1
fi

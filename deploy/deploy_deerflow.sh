#!/bin/bash
#
# DeerFlow 完整部署脚本
# 自动配置环境变量并重启 DeerFlow
#
# 用法: bash deploy_deerflow.sh [--skip-db-test]
#

set -e

SKILLS_DIR="/opt/git/water-resources-skills/skills"
DEERFLOW_DIR="/opt/git/deer-flow"
ENV_FILE="/etc/default/deerflow-env"
BACKEND_ENV="$DEERFLOW_DIR/backend/.env"

echo "========================================"
echo "DeerFlow Skill 路径注入部署"
echo "========================================"
echo

# 检查 1: 环境变量文件
echo "[1/5] 检查环境变量配置"
echo "----------------------------------------"
if [ -f "$ENV_FILE" ]; then
    echo "✅ /etc/default/deerflow-env 存在"
    if grep -q "your-password-here" "$ENV_FILE"; then
        echo "⚠️  数据库密码未设置"
        echo
        read -p "请输入 SL323_DB_PASSWORD: " -s DB_PASSWORD
        echo
        sudo sed -i "s/your-password-here/$DB_PASSWORD/" "$ENV_FILE"
        sudo chmod 600 "$ENV_FILE"
        echo "✅ 密码已设置"
    else
        echo "✅ 密码已配置"
    fi
else
    echo "❌ /etc/default/deerflow-env 不存在"
    exit 1
fi
echo

# 检查 2: DeerFlow backend .env
echo "[2/5] 配置 DeerFlow Backend .env"
echo "----------------------------------------"
if [ ! -f "$BACKEND_ENV" ]; then
    echo "创建 backend/.env..."
    sudo cp "$ENV_FILE" "$BACKEND_ENV"
    sudo chmod 600 "$BACKEND_ENV"
    echo "✅ backend/.env 已创建（从 /etc/default/deerflow-env 复制）"
else
    echo "⚠️  backend/.env 已存在"
    echo "   检查是否需要更新..."
    if ! grep -q "WATER_RESOURCES_ROOT" "$BACKEND_ENV"; then
        echo "   添加 WATER_RESOURCES_ROOT..."
        echo "WATER_RESOURCES_ROOT=/mnt/skills" | sudo tee -a "$BACKEND_ENV" > /dev/null
    fi
    echo "✅ backend/.env 已更新"
fi
echo

# 检查 3: 停止 DeerFlow
echo "[3/5] 停止 DeerFlow 服务"
echo "----------------------------------------"
cd "$DEERFLOW_DIR"
if make stop 2>/dev/null; then
    echo "✅ DeerFlow 已停止"
    sleep 2
else
    echo "⚠️  DeerFlow 未运行或停止失败"
fi
echo

# 检查 4: 启动 DeerFlow
echo "[4/5] 启动 DeerFlow"
echo "----------------------------------------"
cd "$DEERFLOW_DIR"

# 启动 DeerFlow（后台）
echo "启动 DeerFlow Gateway..."
cd "$DEERFLOW_DIR"

# 导出环境变量到 DeerFlow 启动脚本
export WATER_RESOURCES_ROOT=/mnt/skills
export SL323_DB_HOST=192.168.100.103
export SL323_DB_PORT=3306
export SL323_DB_USER=root
export SL323_DB_PASSWORD=$(grep SL323_DB_PASSWORD "$BACKEND_ENV" | cut -d= -f2)

echo "环境变量:"
echo "  WATER_RESOURCES_ROOT=$WATER_RESOURCES_ROOT"
echo "  SL323_DB_HOST=$SL323_DB_HOST"
echo "  SL323_DB_PORT=$SL323_DB_PORT"
echo "  SL323_DB_USER=$SL323_DB_USER"
echo

# 使用 make dev 启动（开发模式，带 hot-reload）
echo "启动 DeerFlow (make dev)..."
nohup make dev > /tmp/deerflow-start.log 2>&1 &
DEERFLOW_PID=$!
echo "PID: $DEERFLOW_PID"
echo

# 等待启动
echo "等待服务就绪..."
sleep 5

# 检查是否启动成功
if ps -p $DEERFLOW_PID > /dev/null 2>&1; then
    echo "✅ DeerFlow 已启动（PID: $DEERFLOW_PID）"
else
    echo "❌ DeerFlow 启动失败"
    echo "查看日志:"
    tail -20 /tmp/deerflow-start.log
    exit 1
fi
echo

# 检查 5: 验证部署
echo "[5/5] 验证部署"
echo "----------------------------------------"

# 检查环境变量
if tr '\0' '\n' < /proc/$DEERFLOW_PID/environ 2>/dev/null | grep -q "WATER_RESOURCES_ROOT=/mnt/skills"; then
    echo "✅ WATER_RESOURCES_ROOT 已注入到 DeerFlow 进程"
else
    echo "⚠️  WATER_RESOURCES_ROOT 未注入到进程"
    echo "   检查 backend/.env 是否正确加载"
fi

# 检查端口
if ss -ltn "( sport = :8001 )" 2>/dev/null | grep -q .; then
    echo "✅ Gateway 端口 8001 正在监听"
else
    echo "⚠️  Gateway 端口 8001 未就绪"
fi

echo
echo "========================================"
echo "部署完成"
echo "========================================"
echo
echo "下一步:"
echo "  1. 等待 10-15 秒让服务完全启动"
echo "  2. 运行完整验证:"
echo "     cd $SKILLS_DIR"
echo "     bash scripts/deerflow_path_injection_test.sh"
echo "  3. 在线测试:"
echo "     访问 http://localhost:2026"
echo "     查询: '古运河有哪些水位测站？'"
echo
echo "日志位置:"
echo "  Gateway: $DEERFLOW_DIR/logs/gateway.log"
echo "  Frontend: $DEERFLOW_DIR/logs/frontend.log"
echo "  Nginx: $DEERFLOW_DIR/logs/nginx.log"
echo

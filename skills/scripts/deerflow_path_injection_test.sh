#!/bin/bash
#
# DeerFlow Skill 路径注入验证脚本
# 在 DeerFlow 环境外部验证 path mapping 和 WATER_RESOURCES_ROOT 配置
#
# 用法: bash deerflow_path_injection_test.sh
#

set -e

SKILLS_DIR="/opt/git/water-resources-skills/skills"
DEERFLOW_CONFIG="/opt/git/deer-flow/config.yaml"
SANDBOX_SCRIPT="/opt/git/water-resources-skills/skills/scripts/deerflow_verify_paths.py"

echo "========================================"
echo "DeerFlow Skill 路径注入验证"
echo "========================================"
echo

# 检查 1: DeerFlow 配置
echo "[检查 1] DeerFlow config.yaml"
echo "----------------------------------------"
if [ -f "$DEERFLOW_CONFIG" ]; then
    echo "✅ config.yaml 存在: $DEERFLOW_CONFIG"
    grep -A 3 "^skills:" "$DEERFLOW_CONFIG" | sed 's/^/   /'
else
    echo "❌ config.yaml 不存在"
    exit 1
fi
echo

# 检查 2: Skills 目录结构
echo "[检查 2] Skills 目录结构"
echo "----------------------------------------"
if [ -d "$SKILLS_DIR" ]; then
    echo "✅ skills/ 目录存在: $SKILLS_DIR"
    echo "   lib/:      $(ls -1d $SKILLS_DIR/lib 2>/dev/null || echo '❌ 不存在')"
    echo "   shared/:   $(ls -1d $SKILLS_DIR/shared 2>/dev/null || echo '❌ 不存在')"
    echo "   water-situation/: $(ls -1d $SKILLS_DIR/water-situation 2>/dev/null || echo '❌ 不存在')"
else
    echo "❌ skills/ 目录不存在"
    exit 1
fi
echo

# 检查 3: WATER_RESOURCES_ROOT 环境变量（当前 shell）
echo "[检查 3] 环境变量配置"
echo "----------------------------------------"
if [ -n "$WATER_RESOURCES_ROOT" ]; then
    echo "✅ WATER_RESOURCES_ROOT=$WATER_RESOURCES_ROOT"
    if [ -d "$WATER_RESOURCES_ROOT" ]; then
        echo "✅ 路径存在: $WATER_RESOURCES_ROOT"
    else
        echo "⚠️  路径不存在: $WATER_RESOURCES_ROOT"
    fi
else
    echo "⚠️  WATER_RESOURCES_ROOT 未在当前 shell 设置"
    echo "   执行: export WATER_RESOURCES_ROOT=/mnt/skills"
fi
echo

# 检查 4: Systemd Service 配置
echo "[检查 4] Systemd Service 配置"
echo "----------------------------------------"
SERVICE_OVERRIDE="/etc/systemd/system/deerflow.service.d/override.conf"
ENV_FILE="/etc/default/deerflow-env"

if [ -f "$ENV_FILE" ]; then
    echo "✅ EnvironmentFile 存在: $ENV_FILE"
    echo "   内容:"
    grep "WATER_RESOURCES_ROOT" "$ENV_FILE" | sed 's/^/     /'
else
    echo "⚠️  EnvironmentFile 不存在: $ENV_FILE"
    echo "   创建命令:"
    echo "   sudo tee $ENV_FILE > /dev/null << 'EOF'"
    echo "   WATER_RESOURCES_ROOT=/mnt/skills"
    echo "   SL323_DB_HOST=192.168.100.103"
    echo "   SL323_DB_PORT=3306"
    echo "   SL323_DB_USER=root"
    echo "   SL323_DB_PASSWORD=your-password"
    echo "   EOF"
fi

if [ -d "/etc/systemd/system/deerflow.service.d" ]; then
    echo "✅ Service override 目录存在"
    if [ -f "$SERVICE_OVERRIDE" ]; then
        echo "✅ Override 配置存在: $SERVICE_OVERRIDE"
        cat "$SERVICE_OVERRIDE" | sed 's/^/     /'
    else
        echo "⚠️  Override 配置不存在"
    fi
else
    echo "⚠️  Service override 目录不存在"
fi
echo

# 检查 5: DeerFlow 进程状态
echo "[检查 5] DeerFlow 进程状态"
echo "----------------------------------------"
if systemctl is-active --quiet deerflow 2>/dev/null; then
    echo "✅ deerflow service 正在运行"
    echo "   PID: $(systemctl show deerflow -p MainPID | cut -d= -f2)"

    # 检查环境变量是否注入到 running process
    DEERFLOW_PID=$(systemctl show deerflow -p MainPID | cut -d= -f2)
    if [ -n "$DEERFLOW_PID" ] && [ "$DEERFLOW_PID" != "0" ]; then
        ENV_VAR=$(tr '\0' '\n' < /proc/$DEERFLOW_PID/environ 2>/dev/null | grep WATER_RESOURCES_ROOT || echo "")
        if [ -n "$ENV_VAR" ]; then
            echo "✅ 环境变量已注入到进程: $ENV_VAR"
        else
            echo "⚠️  环境变量未注入到进程"
        fi
    fi
else
    echo "⚠️  deerflow service 未运行"
fi
echo

# 检查 6: 运行验证脚本
echo "[检查 6] 路径解析验证"
echo "----------------------------------------"
if [ -f "$SANDBOX_SCRIPT" ]; then
    echo "✅ 验证脚本存在: $SANDBOX_SCRIPT"
    echo "   执行验证..."
    echo

    # 先尝试导入 WATER_RESOURCES_ROOT
    if [ -n "$WATER_RESOURCES_ROOT" ]; then
        python3 "$SANDBOX_SCRIPT"
    else
        echo "⚠️  跳过验证（WATER_RESOURCES_ROOT 未设置）"
        echo "   设置后运行: python3 $SANDBOX_SCRIPT"
    fi
else
    echo "❌ 验证脚本不存在: $SANDBOX_SCRIPT"
fi
echo

# 检查 7: 文档存在性
echo "[检查 7] 文档配置"
echo "----------------------------------------"
if [ -f "/opt/git/water-resources-skills/skills/docs/deerflow-deployment.md" ]; then
    echo "✅ 部署文档存在: skills/docs/deerflow-deployment.md"
else
    echo "⚠️  部署文档不存在"
fi
echo

echo "========================================"
echo "验证完成"
echo "========================================"
echo
echo "下一步:"
echo "  1. 创建 /etc/default/deerflow-env（如尚未创建）"
echo "  2. 创建 systemd override（如尚未创建）"
echo "  3. sudo systemctl daemon-reload && sudo systemctl restart deerflow"
echo "  4. 重新运行此脚本验证"
echo

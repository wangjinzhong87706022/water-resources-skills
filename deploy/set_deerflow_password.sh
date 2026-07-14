#!/bin/bash
#
# DeerFlow 数据库密码设置脚本
# 安全: 密码仅在本地终端显示，不会进入日志
#
# 用法: bash set_deerflow_password.sh
#

set -e

ENV_FILE="/etc/default/deerflow-env"
BACKEND_DIR="/opt/git/deer-flow/backend"
BACKUP_FILE="/etc/default/deerflow-env.bak.$(date +%Y%m%d_%H%M%S)"

echo "========================================"
echo "DeerFlow 数据库密码设置"
echo "========================================"
echo

# 检查权限
if [ ! -w "$ENV_FILE" ]; then
    echo "❌ 无法写入 $ENV_FILE"
    echo "   请使用 sudo 运行: sudo bash $0"
    exit 1
fi

# 备份原文件
echo "[1/4] 备份配置文件"
echo "----------------------------------------"
cp "$ENV_FILE" "$BACKUP_FILE"
echo "✅ 已备份到: $BACKUP_FILE"
echo

# 检查当前状态
echo "[2/4] 检查当前配置"
echo "----------------------------------------"
if grep -q "your-password-here" "$ENV_FILE"; then
    echo "⚠️  数据库密码未设置"
else
    echo "✅ 密码已配置（将重新设置）"
fi
echo

# 提示用户输入密码
echo "[3/4] 输入数据库密码"
echo "----------------------------------------"
echo "请输入 SL323 数据库密码（输入时不会显示）"
read -s -p "密码: " DB_PASSWORD
echo
echo "确认密码"
read -s -p "再次输入: " DB_PASSWORD_CONFIRM
echo

if [ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]; then
    echo "❌ 两次密码不一致"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ 密码不能为空"
    exit 1
fi

# 更新密码
echo "[4/4] 更新配置"
echo "----------------------------------------"
sed -i.bak "s/your-password-here/$DB_PASSWORD/" "$ENV_FILE"
chmod 600 "$ENV_FILE"
echo "✅ 密码已更新到: $ENV_FILE"
echo

# 验证
echo "验证配置（隐藏密码）"
grep -E "WATER_RESOURCES_ROOT|SL323_DB_HOST|SL323_DB_PORT|SL323_DB_USER" "$ENV_FILE" | sed 's/=.*/=***/'
echo

# 配置 DeerFlow backend .env
echo "配置 DeerFlow Backend .env"
echo "----------------------------------------"
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$ENV_FILE" "$BACKEND_DIR/.env"
    chmod 600 "$BACKEND_DIR/.env"
    echo "✅ backend/.env 已创建"
else
    # 更新 WATER_RESOURCES_ROOT
    if ! grep -q "WATER_RESOURCES_ROOT" "$BACKEND_DIR/.env"; then
        echo "WATER_RESOURCES_ROOT=/mnt/skills" >> "$BACKEND_DIR/.env"
    fi
    # 更新数据库配置
    sed -i.bak "s/^SL323_DB_HOST=.*/SL323_DB_HOST=192.168.100.103/" "$BACKEND_DIR/.env"
    sed -i.bak "s/^SL323_DB_PORT=.*/SL323_DB_PORT=3306/" "$BACKEND_DIR/.env"
    sed -i.bak "s/^SL323_DB_USER=.*/SL323_DB_USER=root/" "$BACKEND_DIR/.env"
    sed -i.bak "s/^SL323_DB_PASSWORD=.*/SL323_DB_PASSWORD=$DB_PASSWORD/" "$BACKEND_DIR/.env"
    chmod 600 "$BACKEND_DIR/.env"
    echo "✅ backend/.env 已更新"
fi
echo

echo "========================================"
echo "✅ 密码设置完成"
echo "========================================"
echo
echo "下一步: 重启 DeerFlow"
echo "  cd /opt/git/deer-flow"
echo "  make stop"
echo "  make gateway"
echo
echo "或使用自动化部署脚本:"
echo "  bash /opt/git/water-resources-skills/deploy/deploy_deerflow.sh"
echo

# DeerFlow 环境变量配置（待编辑）

**重要**: 在启动 DeerFlow 之前，必须先设置数据库密码！

## 当前状态

✅ WATER_RESOURCES_ROOT=/mnt/skills 已配置
✅ Systemd override 已部署
⏳ 等待设置数据库密码

## 设置密码步骤

### 方法 1: 编辑环境变量文件（推荐）

```bash
sudo nano /etc/default/deerflow-env
```

找到这一行：
```
SL323_DB_PASSWORD=your-password-here
```

替换为实际密码：
```
SL323_DB_PASSWORD=<SECRET_d82484ab>ord
```

保存退出（Ctrl+X → Y → Enter）

### 方法 2: 测试时临时设置（快速测试用）

如果只是想快速测试，可以在运行验证脚本前临时导出：

```bash
export SL323_DB_PASSWORD=<SECRET_d82484ab>ord
```

## 重启 DeerFlow

设置密码后，重启 DeerFlow：

```bash
# 找到 DeerFlow 进程
DEERFLOW_PID=$(pgrep -f "uvicorn app.gateway.app:app" | head -1)

# 终止旧进程
kill $DEERFLOW_PID

# 在 DeerFlow 目录重新启动
cd /opt/git/deer-flow
make gateway
```

或在后台启动：

```bash
cd /opt/git/deer-flow/backend
nohup make gateway > ../logs/gateway.log 2>&1 &
```

## 验证

重启后，运行验证脚本：

```bash
cd /opt/git/water-resources-skills/skills
bash scripts/deerflow_path_injection_test.sh
```

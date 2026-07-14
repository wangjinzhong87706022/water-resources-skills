# DeerFlow 环境变量注入配置

本文件说明如何通过 systemd service override 为 DeerFlow 注入环境变量。

## 文件清单

| 文件 | 用途 | 优先级 |
|------|------|--------|
| `/etc/default/deerflow-env` | 环境变量定义文件（推荐） | 高 |
| `/etc/systemd/system/deerflow.service.d/override.conf` | Systemd service override | 高 |
| `/opt/git/deer-flow/backend/.env` | Docker Compose / 本地开发备选 | 中 |
| `docker-compose.yml` 环境变量节 | 容器化部署 | 高 |

## 快速部署

### Step 1: 创建 EnvironmentFile

```bash
sudo tee /etc/default/deerflow-env > /dev/null << 'EOF'
# DeerFlow Skill 路径注入配置
# 文件: /etc/default/deerflow-env

# Skill 根目录（指向 water-resources-skills 仓库）
WATER_RESOURCES_ROOT=/mnt/skills

# 数据库配置
SL323_DB_HOST=192.168.100.103
SL323_DB_PORT=3306
SL323_DB_USER=root
SL323_DB_PASSWORD=<SECRET_d82484ab>ord
EOF
```

### Step 2: 创建 Systemd Override

```bash
sudo mkdir -p /etc/systemd/system/deerflow.service.d
sudo tee /etc/systemd/system/deerflow.service.d/override.conf > /dev/null << 'EOF'
[Service]
EnvironmentFile=/etc/default/deerflow-env
EOF
```

### Step 3: 重启并验证

```bash
sudo systemctl daemon-reload
sudo systemctl restart deerflow
sudo systemctl show deerflow -p Environment | grep WATER_RESOURCES
```

## 验证

运行验证脚本：

```bash
cd /opt/git/water-resources-skills/skills
bash scripts/deerflow_path_injection_test.sh
```

或直接运行 Python 验证：

```bash
WATER_RESOURCES_ROOT=/mnt/skills python3 scripts/deerflow_verify_paths.py
```

## 故障排除

### 环境变量未注入

检查进程环境：

```bash
DEERFLOW_PID=$(systemctl show deerflow -p MainPID | cut -d= -f2)
tr '\0' '\n' < /proc/$DEERFLOW_PID/environ | grep WATER_RESOURCES
```

### Systemd Override 未生效

检查服务文件目录优先级：

```bash
systemctl show deerflow -p FragmentPath
# 应显示 /etc/systemd/system/deerflow.service.d/override.conf
```

### DeerFlow config.yaml 路径不匹配

确认 `skills.path` 指向本仓库：

```bash
grep -A 3 "^skills:" /opt/git/deer-flow/config.yaml
# 期望输出: path: /opt/git/water-resources-skills/skills
```

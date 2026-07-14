# DeerFlow Skill 路径注入验证指南

本指南说明如何配置 DeerFlow 以正确使用改造后的 skill 文件引用机制。

## 环境变量配置

### 方法 1: Systemd Service（推荐）

#### 1.1 创建 EnvironmentFile

创建 `/etc/default/deerflow-env`：

```bash
sudo tee /etc/default/deerflow-env > /dev/null << 'EOF'
# DeerFlow Skill 路径注入配置
# 文件: /etc/default/deerflow-env

# Skill 根目录（指向 water-resources-skills 仓库）
WATER_RESOURCES_ROOT=/mnt/skills

# 数据库配置（从 water-resources-skills .env 同步）
SL323_DB_HOST=192.168.100.103
SL323_DB_PORT=3306
SL323_DB_USER=root
SL323_DB_PASSWORD=<SECRET_d82484ab>ord  # ← 替换为实际密码

# Hermes 路径（如 Hermes 与 DeerFlow 共享配置）
HERMES_SKILL_DIR=/root/.hermes/skills/water-resources
EOF
```

#### 1.2 创建 Systemd Service Override

创建 `/etc/systemd/system/deerflow.service.d/override.conf`：

```bash
sudo mkdir -p /etc/systemd/system/deerflow.service.d
sudo tee /etc/systemd/system/deerflow.service.d/override.conf > /dev/null << 'EOF'
[Service]
EnvironmentFile=/etc/default/deerflow-env
EOF
```

#### 1.3 重启 DeerFlow Service

```bash
sudo systemctl daemon-reload
sudo systemctl restart deerflow
```

#### 1.4 验证环境变量已注入

```bash
sudo systemctl show deerflow -p Environment | grep WATER_RESOURCES
# 期望输出: Environment=WATER_RESOURCES_ROOT=/mnt/skills ...
```

### 方法 2: Docker Compose（容器化部署）

编辑 `/opt/git/deer-flow/docker-compose.yml`：

```yaml
services:
  backend:
    environment:
      # Skill 路径注入
      - WATER_RESOURCES_ROOT=/mnt/skills
      # 数据库配置
      - SL323_DB_HOST=192.168.100.103
      - SL323_DB_PORT=3306
      - SL323_DB_USER=root
      - SL323_DB_PASSWORD=<SECRET_d82484ab>ord  # ← 替换
```

重启容器：

```bash
cd /opt/git/deer-flow
docker-compose restart backend
```

### 方法 3: .env 文件（本地开发）

在 DeerFlow 后端目录创建 `.env`：

```bash
cd /opt/git/deer-flow/backend
cat > .env << 'EOF'
WATER_RESOURCES_ROOT=/mnt/skills
SL323_DB_HOST=192.168.100.103
SL323_DB_PORT=3306
SL323_DB_USER=root
SL323_DB_PASSWORD=<SECRET_d82484ab>ord  # ← 替换
EOF
```

修改启动脚本加载 `.env`：

```bash
# backend/start.sh 或类似启动脚本
export $(grep -v '^#' .env | xargs)
uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001
```

## 验证步骤

### 3.1 静态路径检查

```bash
# 进入 skills 目录
cd /opt/git/water-resources-skills/skills

# 运行验证脚本
python3 scripts/deerflow_verify_paths.py
```

期望输出：
```
[1] 环境变量检查
✅ WATER_RESOURCES_ROOT=/mnt/skills

[2] lib/ 目录验证
✅ lib/db.py 存在

[3] shared/ 目录验证
✅ shared/db_connection.md 存在

[4] water-situation skill 验证
✅ water-situation/SKILL.md 存在

[5] 测试标准导入片段
✅ 成功导入 db.query 和 db.query_multi

[6] 测试实际数据库查询
✅ 查询成功: sl323.st_stbprp_b 共有 X 个测站

[7] 测试 bootstrap 解析器
✅ bootstrap.locate_lib()  = /mnt/skills/lib
✅ bootstrap.locate_shared() = /mnt/skills/shared

✅ 所有验证通过！
```

### 3.2 DeerFlow 在线测试

通过 DeerFlow Web UI 或 API 发送测试查询：

```bash
# 测试 1: 查询水位测站
curl -X POST http://localhost:8001/api/agents/water-situation/query \
  -H "Content-Type: application/json" \
  -d '{"query": "古运河有哪些水位测站？"}'

# 期望: 返回水位测站列表，无 ModuleNotFoundError
```

### 3.3 检查 DeerFlow 日志

```bash
# 查看 backend 日志
sudo journalctl -u deerflow -f | grep -E "db|import|ModuleNotFoundError"

# 期望: 无 import 错误
```

## 常见问题

### Q1: 注入环境变量后仍找不到 db 模块

**原因**: DeerFlow sandbox 环境未继承父进程环境变量。

**解决**:
1. 确认 systemd service override 正确加载
   ```bash
   sudo systemctl show deerflow -p EnvironmentFile
   ```
2. 检查 DeerFlow backend 进程的环境变量
   ```bash
   ps aux | grep uvicorn | grep deerflow
   cat /proc/<pid>/environ | tr '\0' '\n' | grep WATER_RESOURCES
   ```

### Q2: 数据库连接失败

**原因**: `SL323_DB_PASSWORD` 未设置或错误。

**解决**:
```bash
# 测试密码
mysql -h 192.168.100.103 -u root -p -e "SELECT 1"
```

### Q3: 路径验证脚本报 lib/ 不存在

**原因**: `/mnt/skills` 映射未生效或路径错误。

**解决**:
```bash
# 检查 DeerFlow config.yaml
cat /opt/git/deer-flow/config.yaml | grep -A 3 "^skills:"

# 检查实际挂载点
ls -la /mnt/skills 2>/dev/null || echo "/mnt/skills 不存在"
```

## 验收标准

改造成功必须满足以下所有条件：

- ✅ `WATER_RESOURCES_ROOT=/mnt/skills` 已注入 DeerFlow 环境
- ✅ `python3 scripts/deerflow_verify_paths.py` 全部通过
- ✅ DeerFlow Web UI 查询 "古运河有哪些水位测站" 成功返回
- ✅ DeerFlow 日志无 `ModuleNotFoundError: db`
- ✅ DeerFlow 日志无 `KeyError: WATER_RESOURCES_ROOT`

## 下一步

一旦验证通过：
1. ✅ 将此配置文档化到 `CLAUDE.md`
2. ✅ 提交 systemd service 配置到 `deploy/deerflow.service.d/override.conf`
3. ✅ 通知运维团队将此配置纳入生产部署

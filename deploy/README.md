# DeerFlow Skill 路径注入完整方案

本目录包含 DeerFlow skill 路径注入测试验证的完整方案。

## 📋 目录结构

```
deploy/                                    # 部署配置
├── deerflow-env                          # 环境变量配置模板
└── deerflow.service.d/override.conf      # Systemd override

skills/
├── docs/
│   ├── deerflow-deployment.md           # 完整部署验证指南
│   └── systemd-env-injection.md         # Systemd 快速参考
└── scripts/
    ├── deerflow_verify_paths.py         # Python 验证脚本
    └── deerflow_path_injection_test.sh  # Bash 集成测试
```

## 🎯 核心设计

**单一环境变量根**（与 `CLAUDE_PLUGIN_ROOT` 同构）：

```bash
WATER_RESOURCES_ROOT=/mnt/skills  # DeerFlow 虚拟路径
```

**标准导入片段**（LLM 运行时）：

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi
```

## 🚀 快速部署

### 方法 1: Systemd（推荐）

```bash
# 1. 部署环境变量
sudo cp deploy/deerflow-env /etc/default/deerflow-env
sudo chmod 600 /etc/default/deerflow-env
sudo nano /etc/default/deerflow-env  # 编辑数据库密码

# 2. 部署 Systemd Override
sudo cp deploy/deerflow.service.d/override.conf \
  /etc/systemd/system/deerflow.service.d/
sudo systemctl daemon-reload
sudo systemctl restart deerflow

# 3. 验证
bash skills/scripts/deerflow_path_injection_test.sh
```

### 方法 2: Docker Compose

编辑 `deer-flow/docker-compose.yml`：

```yaml
services:
  backend:
    environment:
      - WATER_RESOURCES_ROOT=/mnt/skills
      - SL323_DB_HOST=192.168.100.103
      - SL323_DB_PORT=3306
      - SL323_DB_USER=root
      - SL323_DB_PASSWORD=<SECRET_d82484ab>ord
```

重启：

```bash
cd /opt/git/deer-flow
docker-compose restart backend
```

### 方法 3: .env 文件（本地开发）

```bash
cd /opt/git/deer-flow/backend
cat > .env << 'EOF'
WATER_RESOURCES_ROOT=/mnt/skills
SL323_DB_HOST=192.168.100.103
SL323_DB_PORT=3306
SL323_DB_USER=root
SL323_DB_PASSWORD=<SECRET_d82484ab>ord
EOF
```

## ✅ 验证

### 快速验证（5 秒）

```bash
cd /opt/git/water-resources-skills/skills
bash scripts/deerflow_path_injection_test.sh
```

期望输出：

```
[检查 1] DeerFlow config.yaml ✅
[检查 2] skills/ 目录结构 ✅
[检查 3] 环境变量配置 ✅
[检查 4] Systemd Service 配置 ✅
[检查 5] DeerFlow 进程状态 ✅
[检查 6] 路径解析验证 ✅
   ✅ lib/db.py 存在
   ✅ bootstrap.locate_lib() 定位正确
   ✅ 数据库查询成功
[检查 7] 文档配置 ✅
```

### 完整验证（Python 脚本）

```bash
WATER_RESOURCES_ROOT=/mnt/skills python3 scripts/deerflow_verify_paths.py
```

### 在线测试

访问 DeerFlow Web UI: http://localhost:8001

查询测试用例：
- "古运河有哪些水位测站？"
- "查询宝应水位站最近30天水位数据"

期望结果：无 `ModuleNotFoundError: db`，返回正确数据。

## 🔍 故障排除

### 问题 1: `/mnt/skills` 路径不存在

**原因**: DeerFlow 使用虚拟路径，通过 PathMapping 映射到实际路径。

**解决**: 确认 DeerFlow `config.yaml` 正确：

```bash
grep -A 3 "^skills:" /opt/git/deer-flow/config.yaml
# 期望: path: /opt/git/water-resources-skills/skills
```

### 问题 2: 环境变量未注入到 DeerFlow 进程

**诊断**:

```bash
DEERFLOW_PID=$(systemctl show deerflow -p MainPID | cut -d= -f2)
tr '\0' '\n' < /proc/$DEERFLOW_PID/environ | grep WATER_RESOURCES
```

**解决**: 确认 override 已生效：

```bash
systemctl show deerflow -p FragmentPath
# 应显示 /etc/systemd/system/deerflow.service.d/override.conf
```

### 问题 3: 数据库连接失败

**诊断**:

```bash
mysql -h 192.168.100.103 -u root -p -e "SELECT 1"
```

**解决**: 确认 `.env` 文件中的 `SL323_DB_PASSWORD` 正确。

## 📚 文档索引

- **部署指南**: [docs/deerflow-deployment.md](deerflow-deployment.md)
- **Systemd 参考**: [docs/systemd-env-injection.md](systemd-env-injection.md)
- **设计文档**: ../docs/skill-file-reference-design.md
- **验证脚本**: scripts/deerflow_verify_paths.py
- **集成测试**: scripts/deerflow_path_injection_test.sh

## 📝 修改历史

| Commit | 内容 |
|--------|------|
| `fc38b66` | 双平台文件引用统一（环境变量 + bootstrap） |
| `94c573c` | 新增验证脚本和集成测试 |
| `ee860cd` | 新增 Systemd override 配置 |

## 🤝 贡献

如需添加新的验证项或部署方法，请参考现有文档格式。

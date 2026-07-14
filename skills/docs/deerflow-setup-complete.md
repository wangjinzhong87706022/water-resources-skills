# DeerFlow 完整部署指南

## 📋 目录

- [快速开始](#快速开始)
- [配置环境变量](#配置环境变量)
- [重启 DeerFlow](#重启-deerflow)
- [验证测试](#验证测试)
- [故障排除](#故障排除)

---

## 快速开始

DeerFlow 不是通过 systemd 运行的，而是通过 `make gateway` 或 `./scripts/serve.sh` 启动。

### 前提条件

- ✅ DeerFlow 已安装并运行
- ✅ water-resources-skills 仓库已克隆
- ✅ WATER_RESOURCES_ROOT=/mnt/skills 已配置（通过 `/etc/default/deerflow-env`）

### 待办

- ⏳ 需要设置数据库密码 `SL323_DB_PASSWORD`

---

## 配置环境变量

### 方法 1: DeerFlow Backend .env 文件（推荐）

DeerFlow 启动时会自动加载 `backend/.env` 文件。

```bash
cd /opt/git/deer-flow/backend

# 创建或编辑 .env 文件
cat > .env << 'EOF'
# Skill 路径注入
WATER_RESOURCES_ROOT=/mnt/skills

# 数据库配置
SL323_DB_HOST=192.168.100.103
SL323_DB_PORT=3306
SL323_DB_USER=root
SL323_DB_PASSWORD=<SECRET_d82484ab>ord  # ← 替换为实际密码
EOF

# 保护密码文件
chmod 600 .env
```

### 方法 2: 在启动脚本前导出

```bash
cd /opt/git/deer-flow

# 在启动前导出环境变量
export WATER_RESOURCES_ROOT=/mnt/skills
export SL323_DB_HOST=192.168.100.103
export SL323_DB_PORT=3306
export SL323_DB_USER=root
export SL323_DB_PASSWORD=<SECRET_d82484ab>ord  # ← 替换

# 启动 DeerFlow
make gateway
```

### 方法 3: Systemd Override（备选）

虽然 DeerFlow 当前不是通过 systemd 运行的，但如果你未来改用 systemd：

```bash
# 已部署（参见 deploy/deerflow.service.d/override.conf）
# 启动命令需要改为: sudo systemctl start deerflow
```

---

## 重启 DeerFlow

### 如果 DeerFlow 正在前台运行（Ctrl+C 停止的）

按 `Ctrl+C` 停止，然后重新启动：

```bash
cd /opt/git/deer-flow
make gateway
```

### 如果 DeerFlow 在后台运行

```bash
# 1. 停止所有服务
cd /opt/git/deer-flow
make stop

# 2. 确认已停止
ps aux | grep uvicorn | grep -v grep
# 期望：无输出

# 3. 重新启动
make gateway
```

### 如果使用 serve.sh 启动

```bash
cd /opt/git/deer-flow
./scripts/serve.sh --dev
```

---

## 验证测试

### 1. 检查环境变量已加载

```bash
cd /opt/git/deer-flow/backend
head -5 .env
```

期望输出：
```
WATER_RESOURCES_ROOT=/mnt/skills
SL323_DB_HOST=192.168.100.103
...
```

### 2. 检查 DeerFlow 进程环境

```bash
DEERFLOW_PID=$(pgrep -f "uvicorn app.gateway.app:app" | head -1)
echo "DeerFlow PID: $DEERFLOW_PID"
tr '\0' '\n' < /proc/$DEERFLOW_PID/environ | grep WATER_RESOURCES
```

期望输出：
```
WATER_RESOURCES_ROOT=/mnt/skills
```

### 3. 运行集成测试

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

### 4. Python 验证脚本

```bash
cd /opt/git/water-resources-skills/skills
python3 scripts/deerflow_verify_paths.py
```

期望输出：
```
[5] 测试标准导入片段
✅ 成功导入 db.query 和 db.query_multi

[6] 测试实际数据库查询
✅ 查询成功: sl323.st_stbprp_b 共有 X 个测站
```

### 5. 在线测试

访问 DeerFlow Web UI: http://localhost:2026

测试查询：
- "古运河有哪些水位测站？"
- "查询宝应水位站最近30天水位数据"
- "查询水位站总数"

期望结果：
- ✅ 无 `ModuleNotFoundError: db` 错误
- ✅ 无 `KeyError: WATER_RESOURCES_ROOT` 错误
- ✅ 正确返回水位测站数据

---

## 故障排除

### 问题 1: 找不到 db 模块

**症状**:
```
ModuleNotFoundError: No module named 'db'
```

**原因**: `WATER_RESOURCES_ROOT` 未设置或路径错误。

**解决**:
```bash
# 1. 检查 .env 文件
cd /opt/git/deer-flow/backend
cat .env | grep WATER_RESOURCES_ROOT

# 2. 检查进程环境
DEERFLOW_PID=$(pgrep -f "uvicorn app.gateway.app:app" | head -1)
tr '\0' '\n' < /proc/$DEERFLOW_PID/environ | grep WATER_RESOURCES

# 3. 如果未设置，停止并重启
make stop
make gateway
```

### 问题 2: 数据库连接失败

**症状**:
```
Can't connect to MySQL server on '192.168.100.103'
```

**原因**: `SL323_DB_PASSWORD` 错误或数据库不可达。

**解决**:
```bash
# 1. 测试密码
mysql -h 192.168.100.103 -u root -p -e "SELECT 1"

# 2. 检查 .env 中的密码
cd /opt/git/deer-flow/backend
grep SL323_DB_PASSWORD .env

# 3. 确认密码正确后重启
make stop
make gateway
```

### 问题 3: /mnt/skills 路径不存在

**症状**:
```
FileNotFoundError: /mnt/skills/lib/db.py
```

**原因**: DeerFlow 使用虚拟路径 `/mnt/skills`，通过 PathMapping 映射到真实路径。

**解决**:
```bash
# 1. 检查 DeerFlow config.yaml
cat /opt/git/deer-flow/config.yaml | grep -A 3 "^skills:"
# 期望输出: path: /opt/git/water-resources-skills/skills

# 2. 确认映射生效
ls -la /mnt/skills 2>/dev/null || echo "/mnt/skills 是虚拟路径，仅在 DeerFlow sandbox 中可用"

# 3. 检查 DeerFlow 日志
tail -50 /opt/git/deer-flow/logs/gateway.log | grep skills
```

### 问题 4: 验证脚本超时

**症状**: `deerflow_verify_paths.py` 数据库查询卡住。

**原因**: 网络或数据库响应慢。

**解决**:
```bash
# 手动测试数据库连接
mysql -h 192.168.100.103 -u root -p -e "SELECT COUNT(*) FROM sl323.st_stbprp_b"

# 如果查询慢，检查网络
ping 192.168.100.103

# 或跳过数据库检查，只验证路径
grep -v "实际数据库查询" /opt/git/water-resources-skills/skills/scripts/deerflow_verify_paths.py
```

---

## 验收标准

✅ 改造成功的标志：

- [ ] `WATER_RESOURCES_ROOT=/mnt/skills` 在 DeerFlow 进程环境中
- [ ] `python3 scripts/deerflow_verify_paths.py` 全部通过
- [ ] DeerFlow Web UI 查询成功返回数据
- [ ] 无 `ModuleNotFoundError: db`
- [ ] 无 `KeyError: WATER_RESOURCES_ROOT`

---

## 下一步

验证通过后：

1. ✅ 将此配置文档化到团队 wiki
2. ✅ 将 `.env` 模板提交到 `deer-flow/backend/.env.example`
3. ✅ 通知其他开发者设置环境变量

---

## 参考文档

- 设计文档: `skills/docs/skill-file-reference-design.md`
- Systemd 参考: `skills/docs/systemd-env-injection.md`
- 部署配置: `deploy/deerflow-env`, `deploy/deerflow.service.d/override.conf`
- 验证脚本: `skills/scripts/deerflow_verify_paths.py`

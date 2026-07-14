# DeerFlow 部署快速开始

## 🚀 三步完成部署

### Step 1: 设置数据库密码（需手动）

由于安全策略，数据库密码需要你本地输入。

```bash
bash /opt/git/water-resources-skills/deploy/set_deerflow_password.sh
```

这个脚本会：
- ✅ 提示你输入密码（输入时不会显示）
- ✅ 自动备份原配置文件
- ✅ 更新 `/etc/default/deerflow-env`
- ✅ 配置 DeerFlow `backend/.env`
- ✅ 验证配置（不显示密码）

### Step 2: 重启 DeerFlow（自动或手动）

**方法 A: 使用自动化脚本**（推荐）

```bash
bash /opt/git/water-resources-skills/deploy/deploy_deerflow.sh
```

**方法 B: 手动重启**

```bash
cd /opt/git/deer-flow
make stop
make gateway
```

### Step 3: 验证部署（自动）

```bash
cd /opt/git/water-resources-skills/skills
bash scripts/deerflow_path_injection_test.sh
```

期望输出：7 个检查项全部 ✅

---

## 📋 完整清单

- [x] 环境变量配置文件已部署
- [x] Systemd override 已部署
- [x] 测试脚本已创建
- [x] 文档已齐全
- [ ] **需要你完成**: 设置数据库密码
- [ ] **需要你完成**: 重启 DeerFlow
- [ ] **需要你完成**: 运行验证测试

---

## 📚 文档索引

| 文档 | 用途 |
|------|------|
| `deploy/set_deerflow_password.sh` | 密码设置脚本 |
| `deploy/deploy_deerflow.sh` | 自动化部署脚本 |
| `skills/docs/deerflow-setup-complete.md` | 完整部署指南 |
| `skills/docs/deerflow-deployment.md` | 验证测试指南 |

---

## 🔍 故障排除

如果遇到问题，参考：
- 完整指南: `skills/docs/deerflow-setup-complete.md`
- 验证指南: `skills/docs/deerflow-deployment.md`

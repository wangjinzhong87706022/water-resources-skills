# 数据库配置环境变量化修复总结

**修复时间**: 2026-07-14
**问题**: 硬编码数据库连接信息（192.168.100.103:3306），部署时需手动修改

---

## 修复内容

### 1. 新增统一配置模块

**文件**: `skills/scripts/config.py`

提供两个函数：
- `get_db_config(database='sl323')` — 从环境变量读取配置
- `get_default_db_config()` — 获取默认 sl323 库配置

**环境变量支持**：
- `SL323_DB_HOST`（默认 192.168.100.103）
- `SL323_DB_PORT`（默认 3306）
- `SL323_DB_USER`（默认 root）
- `SL323_DB_PASSWORD`（必填）

### 2. 更新脚本使用环境变量

| 脚本 | 修改前 | 修改后 |
|------|--------|--------|
| `evaluate_skills.py` | `DEFAULT_DB_CONFIG = {"host": "192.168.100.103", ...}` | `DEFAULT_DB_CONFIG = get_default_db_config()` |
| `autoresearch.py` | `pymysql.connect(host="192.168.100.103", ...)` | `db_config = get_default_db_config(); pymysql.connect(**db_config)` |
| `recompute_verifiers.py` | `DB = {"host": "192.168.100.103", ...}` | `DB = get_default_db_config()` |

### 3. 更新文档说明

#### `shared/db_connection.md`

**新增"连接参数"表格**：
| 参数 | 环境变量 | 默认值 |
|------|---------|--------|
| Host | `SL323_DB_HOST` | 192.168.100.103 |
| Port | `SL323_DB_PORT` | 3306 |
| User | `SL323_DB_USER` | root |
| Password | `SL323_DB_PASSWORD` | （必填） |

**新增"环境变量配置"示例**：
```bash
export SL323_DB_HOST=192.168.100.103
export SL323_DB_PORT=3306
export SL323_DB_USER=root
export SL323_DB_PASSWORD='your-password'
```

**新增"db.py 自动读取环境变量"说明**（引用 `lib/db.py:17-23`）。

#### `water-situation/SKILL.md`

**Prerequisites 节**：
- ❌ 删除：`MySQL 192.168.100.103:3306`
- ❌ 删除：`host='192.168.100.103', port=3306, user='root'`
- ✅ 改为：`通过环境变量配置（SL323_DB_HOST, SL323_DB_PORT, ...）`

### 4. 核心库（已支持）

`skills/lib/db.py` 已实现环境变量读取：
```python
DB_CONFIG = {
    'host': os.environ.get('SL323_DB_HOST', '192.168.100.103'),
    'port': int(os.environ.get('SL323_DB_PORT', '3306')),
    'user': os.environ.get('SL323_DB_USER', 'root'),
    'password': os.environ.get('SL323_DB_PASSWORD', ''),
    'charset': 'utf8mb4',
}
```

---

## 修改文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `skills/scripts/config.py` | 新增 | 统一配置读取函数 |
| `skills/scripts/evaluate_skills.py` | 修改 | 使用 `get_default_db_config()` |
| `skills/scripts/autoresearch.py` | 修改 | 使用 `get_default_db_config()` |
| `skills/scripts/recompute_verifiers.py` | 修改 | 使用 `get_default_db_config()` |
| `skills/shared/db_connection.md` | 修改 | 新增环境变量配置说明 |
| `skills/water-situation/SKILL.md` | 修改 | Prerequisites 改为环境变量 |
| `skills/lib/db.py` | 不变 | 已支持环境变量 |

---

## 部署说明

### 开发环境

```bash
# 方式1: export
export SL323_DB_PASSWORD='your-password'

# 方式2: .env 文件
echo "SL323_DB_PASSWORD=your-password" > .env
source .env
```

### 生产环境

```bash
# 在部署脚本或 systemd service 中设置
Environment="SL323_DB_HOST=192.168.100.103"
Environment="SL323_DB_PORT=3306"
Environment="SL323_DB_USER=root"
Environment="SL323_DB_PASSWORD=your-password"
```

### Docker 环境

```dockerfile
ENV SL323_DB_HOST=192.168.100.103 \
    SL323_DB_PORT=3306 \
    SL323_DB_USER=root \
    SL323_DB_PASSWORD=your-password
```

---

## 优势

✅ **无需修改代码**：部署时只需设置环境变量
✅ **统一配置**：所有脚本使用统一的 `config.py`
✅ **向后兼容**：提供默认值，不设置环境变量也能运行
✅ **安全性**：密码通过环境变量传入，不硬编码
✅ **可移植性**：同一套代码可在不同环境（开发/测试/生产）运行

---

**提交**: `1134775` refactor(config): 统一使用环境变量配置数据库连接

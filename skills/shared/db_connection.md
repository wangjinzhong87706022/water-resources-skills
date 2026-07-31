# 数据库连接信息

> 所有水利 skill 共用的数据库连接配置。

## 连接参数

**默认值**（可通过环境变量覆盖）：

| 参数 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| Host | `SL323_DB_HOST` | 192.168.100.103 | 数据库主机 |
| Port | `SL323_DB_PORT` | 3306 | 数据库端口 |
| User | `SL323_DB_USER` | root | 用户名 |
| Password | `SL323_DB_PASSWORD` | （必填） | 密码 |
| 权限 | - | 只读 | 只允许查询 |

**环境变量配置**：
```bash
# 方式1: 在 shell 中导出
export SL323_DB_HOST=192.168.100.103
export SL323_DB_PORT=3306
export SL323_DB_USER=root
export SL323_DB_PASSWORD='your-password'

# 方式2: 在 .env 文件中（推荐用于开发）
cat > .env <<EOF
SL323_DB_HOST=192.168.100.103
SL323_DB_PORT=3306
SL323_DB_USER=root
SL323_DB_PASSWORD=your-password
EOF
```

⚠️ **注意**：`.env` 文件已加入 `.gitignore`，不要提交到 Git。

## 数据库清单

| 库名 | 用途 | 使用该库的 Skill |
|------|------|-----------------|
| sl323 | 水利核心数据（水情、雨情、闸泵、测站、防洪指标） | 全部 6 个 water-resources skill |
| sl325 | 水质监测数据 | water-quality, water-warning |
| slztk | 水质预测、水位预测模型 | water-quality, water-forecast |
| powerelf_data | Powerelf 平台业务数据（GNSS、渗流、渗压、墒情、预警、巡检、设备、数据治理） | powerelf-monitor, powerelf-data-governance, powerelf-early-warning, powerelf-inspection, powerelf-chatbi |

## 推荐方式：使用 db.py 助手模块

所有查询**必须**使用 `lib/db.py` 助手模块，不要手写 pymysql 连接代码：

### LLM 运行时（推荐）

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi
```

### 离线脚本（scripts/ 目录）

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lib'))
from bootstrap import locate_lib, locate_shared
from db import query, query_multi
```

**示例查询**：
```python
# 单个查询（默认 sl323 库，30s 超时）
rows = query("SELECT stcd, stnm FROM sl323.st_stbprp_b WHERE sttp='ZZ' LIMIT 10")
for row in rows:
    print(row['stnm'], row['stcd'])

# 指定不同数据库
rows = query("SELECT * FROM wq_pcp_d LIMIT 10", db='sl325')

# 自定义超时（复杂查询最多 60s）
rows = query("SELECT ...", timeout=60)

# 多个查询顺序执行
results = query_multi([
    "SELECT COUNT(*) AS cnt FROM sl323.st_stbprp_b",
    "SELECT MAX(tm) FROM sl323.st_river_r WHERE tm >= '2026-01-01'"
])
```

**db.py 配置解析优先级**（`lib/db.py` `_cfg()`）：`os.environ` → 仓库根 `.env` 文件 → 内置默认值。DeerFlow 沙箱会剥除环境中所有 `*PASSWORD*` 变量，因此密码实际由 `.env` 文件兜底提供——**部署时确保仓库根有 `.env`**。

### 关键特性

- **配置自动解析** — 环境变量优先，`.env` 兜底（沙箱剥除密码类环境变量）
- **每查询 30 秒超时** — pymysql 客户端 `read_timeout`；超时抛 `TimeoutError`，错误信息内含改写建议（派生表 JOIN / tm 范围条件）
- **分区裁剪守卫** — `YEAR(tm)`/`DATE(tm)` 等函数且无 tm 范围条件的 SQL 会被直接拒绝（`ValueError`），避免全分区扫描；确需全扫传 `allow_full_scan=True`
- **返回 list[dict]** — 直接用 `row['列名']` 访问结果
- **空结果自动提示** — stderr 提示检查时间覆盖/列名/过滤值
- **schema 自纠错** — Unknown column/table 错误自动附带 INFORMATION_SCHEMA 真实列清单
- **SQL 安全校验** — 只允许 SELECT/SHOW/DESCRIBE/EXPLAIN 开头（**CTE `WITH` 开头会被拒绝**，改用子查询）
- **get_date_range(table)** — 零扫描获取表时间覆盖（读分区边界），判断数据新鲜度时优先用

## 路径说明

### LLM 运行时（推荐）

**标准写法**（使用 `WATER_RESOURCES_ROOT` 环境变量，双平台通用）：

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi
```

- `WATER_RESOURCES_ROOT` 由部署层设置，指向 `skills/` 目录
- DeerFlow: `/mnt/skills`，Hermes: `~/.hermes/skills/water-resources`，开发: 仓库 `…/skills`
- `__file__` 在 LLM 暂存脚本中不可靠，**不要用** `Path(__file__).parent / 'lib'`

### 离线脚本（scripts/ 目录）

离线脚本从真实路径运行，可使用 `bootstrap.py` 解析器（环境变量优先 + 候选兜底）：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lib'))
from bootstrap import locate_lib, locate_shared
from db import query
```

**优先级**：`WATER_RESOURCES_ROOT` 环境变量 → `WATER_RESOURCES_LIB`/`_SHARED` 显式覆盖 → 候选根兜底（`/mnt/skills`、仓库路径、`~/.hermes/...`）。


## 注意事项

- 跨库查询时使用 `库名.表名` 格式（如 `sl325.wq_pcp_d`）
- pymysql 已预装（由 lib/db.py 内部 import），**🚫 禁止 pip install**（沙箱 externally-managed，pip 必失败）
- **禁止手写 pymysql.connect() 连接代码**——沙箱剥除密码环境变量，手写连接拿不到密码必失败；一律走 db.py
- **部署时无需修改代码**：通过环境变量 + `.env` 配置连接信息

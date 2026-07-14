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

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from db import query, query_multi

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
    "SELECT MAX(tm) FROM sl323.st_river_r WHERE tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
])
```

**db.py 自动从环境变量读取配置**（`lib/db.py:17-23`）：
```python
DB_CONFIG = {
    'host': os.environ.get('SL323_DB_HOST', '192.168.100.103'),
    'port': int(os.environ.get('SL323_DB_PORT', '3306')),
    'user': os.environ.get('SL323_DB_USER', 'root'),
    'password': os.environ.get('SL323_DB_PASSWORD', ''),
    'charset': 'utf8mb4',
}
```

### 关键特性

- **自动环境变量读取** — 连接信息来自环境变量，无需硬编码
- **每查询 30 秒超时** — MySQL 端 `max_execution_time` 强制终止慢查询，避免 300s 整体超时
- **返回 list[dict]** — 直接用 `row['列名']` 访问结果
- **空结果自动提示** — 建议扩大时间范围或检查分区表 tm 条件
- **超时错误含建议** — 提示添加 `WHERE tm >= ...` 以利用分区裁剪
- **SQL 安全校验** — 只允许 SELECT/SHOW/DESCRIBE
- **复杂查询拆分** — 多步查询用 `query_multi()` 或多次 `query()` 调用

## 路径说明

✅ **标准写法**（符合 skill 规范）：
```python
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
```

**适用场景**：
- 脚本文件位于 skill 目录内（`Path(__file__)` 指向 skill 目录中的文件）
- hermes-agent 直接执行 skill 目录中的脚本
- 本地开发测试

**要求**：确保脚本文件保存在 skill 目录中，`Path(__file__)` 才能正确解析到 skill 目录的父目录。

## 备选：原始 pymysql（不推荐）

仅在 db.py 模块不可用时使用：

```python
import pymysql
conn = pymysql.connect(
    host=os.environ.get('SL323_DB_HOST', '192.168.100.103'),
    port=int(os.environ.get('SL323_DB_PORT', '3306')),
    user=os.environ.get('SL323_DB_USER', 'root'),
    password=os.environ.get('SL323_DB_PASSWORD', ''),
    database='sl323'
)
```

## 注意事项

- 跨库查询时使用 `库名.表名` 格式（如 `sl325.wq_pcp_d`）
- 首次使用需确认 pymysql 已安装：`pip install pymysql`
- 所有连接必须使用 `conn.cursor()` 执行查询后关闭：`cursor.close(); conn.close()`
- **部署时无需修改代码**：通过环境变量配置连接信息

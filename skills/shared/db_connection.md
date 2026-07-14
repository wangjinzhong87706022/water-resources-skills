# 数据库连接信息

> 所有水利 skill 共用的数据库连接配置。

## 连接参数

| 参数 | 值 |
|------|-----|
| Host | 192.168.100.103 |
| Port | 3306 |
| User | root |
| Password | <SL323_DB_PASSWORD> |
| 权限 | 只读 |

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
sys.path.insert(0, '/opt/git/deer-flow/skills/public/water-situation/lib')
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

### 关键特性

- **每查询 30 秒超时** — MySQL 端 `max_execution_time` 强制终止慢查询，避免 300s 整体超时
- **返回 list[dict]** — 直接用 `row['列名']` 访问结果
- **空结果自动提示** — 建议扩大时间范围或检查分区表 tm 条件
- **超时错误含建议** — 提示添加 `WHERE tm >= ...` 以利用分区裁剪
- **SQL 安全校验** — 只允许 SELECT/SHOW/DESCRIBE
- **复杂查询拆分** — 多步查询用 `query_multi()` 或多次 `query()` 调用

## 平台适配说明

⚠️ **不同平台的技能目录路径不同**，请根据实际部署环境选择：

| 平台 | lib 路径 | 说明 |
|------|---------|------|
| **DeerFlow** | `/opt/git/deer-flow/skills/public/<skill-name>/lib` | DeerFlow 技能容器路径 |
| **hermes-agent** | `/opt/git/hermes-agent/skills/water-resources/lib` | hermes-agent 技能路径 |
| **Git 仓库** | `Path(__file__).parent / 'lib'` | 本地开发，skill 目录内部 |

**查找方法**（路径不确定时）：
```bash
# 查找系统中所有 db.py 位置
find /opt/git -name "db.py" -path "*/lib/*" 2>/dev/null

# 查看当前 skill 的 lib 目录
ls -la /opt/git/deer-flow/skills/public/water-situation/lib/
```

## 备选：原始 pymysql（不推荐）

仅在 db.py 模块不可用时使用：

```python
import pymysql
conn = pymysql.connect(
    host='192.168.100.103', port=3306,
    user='root', password='<SL323_DB_PASSWORD>',
    database='sl323'  # 根据查询场景切换为 sl325 或 slztk
)
```

## 注意事项

- 跨库查询时使用 `库名.表名` 格式（如 `sl325.wq_pcp_d`）
- 首次使用需确认 pymysql 已安装：`pip install pymysql`
- 所有连接必须使用 `conn.cursor()` 执行查询后关闭：`cursor.close(); conn.close()`

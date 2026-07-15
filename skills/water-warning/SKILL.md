---
name: water-warning
description: "水利预警 — 防洪预警（超警戒/超保证水位）和水质预警（水质等级低于Ⅳ类）。核心表: sl323.st_river_r, sl323.st_rvfcch_b, sl325.wq_pcp_d, sl323.st_stbprp_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, warning, alert, flood, water-quality, hydrology, scada]
    category: water-resources
---

# 水利预警 (Water Warning)

防洪预警（超警戒/超保证水位）和水质预警（水质等级低于Ⅳ类）。数据源: MySQL 192.168.100.103:3306，涉及 sl323 + sl325 库。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询哪些站点超警戒水位 | Yes |
| 查询防洪预警汇总 | Yes |
| 查询水位是否超保证水位 | Yes |
| 查询水质预警站点 | Yes |
| 查询水质异常情况（低于Ⅳ类） | Yes |
| 综合防洪+水质预警查询 | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，涉及两个库（只读）
  - sl323: st_river_r, st_rvfcch_b, st_stbprp_b（防洪+测站）
  - sl325: wq_pcp_d（水质监测）
- **pymysql:** execute_code 环境可能未安装，首次使用需先运行 `pip install pymysql`
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）
- 参考 `shared/statistical_methods.md` — 统计分析方法（异常值识别、趋势判断）
- 参考 `shared/analysis_validation.md` — 分析验证（预警报告的置信度评定和陷阱检查）

### 文件引用约定

本 skill 通过**环境变量 `WATER_RESOURCES_ROOT`**（指向 skills/）定位共享资源：

| 引用 | 逻辑路径 | 运行时真实路径（两平台统一） |
|------|---------|---------------------------|
| 共享库 | `lib/db.py` | `$WATER_RESOURCES_ROOT/lib/db.py` |
| 共享文档 | `shared/db_connection.md` | `$WATER_RESOURCES_ROOT/shared/db_connection.md` |
| 共享规则 | `shared/sql_safety_rules.md` | `$WATER_RESOURCES_ROOT/shared/sql_safety_rules.md` |

> `WATER_RESOURCES_ROOT` 由部署层设置：DeerFlow 指向 `/mnt/skills`，Hermes 指向 `~/.hermes/skills/water-resources`，开发指向仓库 `…/skills`。

**标准导入片段**（`__file__` 在 sandbox 暂存脚本中不可靠，勿用）：
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi
```

## Workflow

1. **防洪预警。** 比较 st_river_r.z 与 st_rvfcch_b.WRZ/GRZ。
   - z > WRZ → 黄色预警（超警戒）
   - z > GRZ → 红色预警（超保证）
2. **水质预警。** 查询 sl325.wq_pcp_d 各指标，按 6 级标准评级（单因子评价法），任一指标低于Ⅳ类触发预警。
3. **跨库查询需带库名前缀:** sl325.wq_pcp_d, sl323.st_river_r 等。
4. **质量自检。** 执行 SQL 前确认符合安全规则。特别注意 st_rvfcch_b.STCD 是大写。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。

## Validation Gate

**预警查询交付前必须通过以下检查。**

### 阈值对比方向检查

- [ ] **超警戒/超保证方向正确**：`z > WRZ` → 黄色预警（超警戒），`z > GRZ` → 红色预警（超保证）
- [ ] **级别不混淆**：红色预警（超保证）优先级高于黄色预警（超警戒），不能反过来

**常见错误示例**：
```sql
❌ 错误：z < WRZ → 超警戒（方向反了）
✅ 正确：z > WRZ → 超警戒
```

### 阈值数据存在性检查

- [ ] **查询前验证**：在查询 WRZ/GRZ 前，**必须**验证该测站阈值数据是否存在
  ```sql
  SELECT COUNT(*) as cnt FROM st_rvfcch_b WHERE STCD='目标站码' AND (WRZ IS NOT NULL OR GRZ IS NOT NULL)
  ```
- [ ] **缺失处理**：若 cnt=0，**跳过阈值查询**，直接告知用户"⚠️ 该站阈值数据缺失"

**参考**：water-situation 的 `references/threshold_query_validation.md`

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl323.st_river_r | 河道水位 | stcd, tm, z |
| sl323.st_rvfcch_b | 防洪指标 | **STCD**(注意大写), WRZ(警戒水位), GRZ(保证水位) |
| sl325.wq_pcp_d | 水质数据 | stcd, **spt**(采样时间), dox, codmn, nh3n, tp |
| sl323.st_stbprp_b | 测站信息 | sttp='ZZ'(水位站)/'WQ'(水质站) |

## Business Rules Summary

- **st_rvfcch_b 无 PK**，STCD 列名是大写（不是小写 stcd）
- **st_rvfcch_b JOIN 条件:** `r.stcd = rv.STCD`（注意大小写）
- **超警戒:** z > WRZ → 黄色预警
- **超保证:** z > GRZ → 红色预警
- **水质预警阈值（Ⅳ类）:** CODMn > 10, DO < 3, NH3N > 1.5, TP > 0.3
- **wq_pcp_d 时间字段是 spt**，不是 tm
- **水质站类型:** sttp='WQ'

## Related Skills

- `water-situation` — 实时水位查询
- `water-quality` — 水质评级详情
- `gate-pump-operation` — 闸泵调度
- `water-visualization` — 预警状态汇总面板图

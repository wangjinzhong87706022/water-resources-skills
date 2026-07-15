---
name: water-forecast
description: "水位预测与模型计算 — 未来水位预报、模型计算结果。核心表: slztk.st_mx_preset_cal_r, slztk.st_mx_taskid_r, slztk.st_mx_rv_dm_r, sl323.st_stbprp_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, forecast, prediction, model, hydrology, scada]
    category: water-resources
---

# 水位预测与模型计算 (Water Forecast)

查询未来水位预报、模型计算结果。数据源: MySQL 192.168.100.103:3306，涉及 slztk + sl323 库。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询未来24小时水位预测 | Yes |
| 查询重点河道未来水位预报 | Yes |
| 查询模型计算任务列表和状态 | Yes |
| 查询河道断面计算结果 | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，slztk(预测表) + sl323(测站表)（只读）
- **pymysql:** execute_code 环境可能未安装，首次使用需先运行 `pip install pymysql`
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）
- 参考 `shared/statistical_methods.md` — 统计分析方法（预测精度评估、偏差分析）
- 参考 `shared/sql_patterns.md` — SQL 通用查询模式（预测 vs 实测跨表对齐）
- 参考 `shared/analysis_validation.md` — 分析验证（预测结果的可信度评定）

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

## Pitfalls

- **最新任务可能很旧。** 预测系统不一定每天运行。先查 `SELECT taskid, tm, stuts FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1` 确认最新任务时间，若距今超过1天，需告知用户数据非实时。可降级查最近已完成任务(stuts=1)。
- **查已完成任务。** 用 `WHERE stuts = 1 ORDER BY tm DESC` 过滤，避免拿到未完成的空任务。

## Workflow

1. **获取最新任务 ID。** `SELECT taskid FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1`
2. **查询预测数据。** 用 taskid 过滤 st_mx_preset_cal_r，type='1' 为水位。
3. **JOIN 测站信息。** 跨库: slztk 表 JOIN sl323.st_stbprp_b。
4. **模型结果。** 可查询 st_mx_rv_dm_r 获取河道断面数据。
5. **质量自检。** 执行 SQL 前确认符合安全规则。预测数据需检查最新任务时间，若距当前超过1天需告知用户。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。

## Validation Gate

**水位预测查询交付前必须通过以下检查。**

### 预测时效性检查

- [ ] **最新任务时间验证**：在查询预测数据前，**必须**先检查最新任务时间
  ```sql
  SELECT taskid, tm, stuts FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1
  ```
- [ ] **时效性判断**：若最新任务距今超过 24 小时，**必须告知用户**"⚠️ 预测数据非实时（最新任务时间：YYYY-MM-DD HH:mm）"
- [ ] **降级策略**：若最新任务未完成(stuts=0)，可降级查询最近已完成任务(stuts=1)

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| slztk.st_mx_preset_cal_r | 预测结果 | taskid, stcd, tm, **type(varchar)**, vals |
| slztk.st_mx_taskid_r | 预测任务 | **uuid**(PK), taskid, tm, stuts, type |
| slztk.st_mx_rv_dm_r | 河道断面 | taskid, name, z, Qin, Qout |
| sl323.st_stbprp_b | 测站信息 | stcd, stnm |

## Business Rules Summary

- **st_mx_preset_cal_r.type 是 varchar(5):** `type = '1'`（水位）不是 `type = 1`
- **st_mx_taskid_r 的 PK 是 uuid**，不是 taskid
- **st_mx_preset_cal_r 无 PK**，只有 INDEX
- **任务状态:** stuts=0 未完成, stuts=1 已完成

## Related Skills

- `water-situation` — 实时水位查询
- `water-warning` — 防洪预警
- `water-visualization` — 预测 vs 实际水位对比图

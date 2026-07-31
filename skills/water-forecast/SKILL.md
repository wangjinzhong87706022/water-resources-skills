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
- **pymysql 已由 lib/db.py 内部处理，🚫 禁止 pip install**（沙箱 externally-managed，pip 必失败且白烧 3-5 个轮次）。
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

- **⚡ 一轮完成（性能第一杠杆，每次 LLM 往返 30-80s）。** taskid 探测 + 时效检查 + EXISTS 回退 + 主查询必须写进**同一个 Python 脚本**一轮执行：先取 taskid，再用 f-string 把实值代入主查询（同脚本内安全；**禁止跨回合留 `{taskid}` 占位符**）。首查就直接用带 EXISTS 的取-taskid SQL（见下），不要等 0 行后再回退多烧一轮。
- **⚡ 预报时间窗必须锚定任务自身时间。** 用该 taskid 下的 `MIN(tm)`~`MAX(tm)`（或任务 tm）圈定窗口，**禁止** `BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)`——最新任务可能很旧，NOW() 窗口与预报 tm 无交集必返 0 行。
- **⚠️ 模糊时间禁止反问。** "未来/近期"等模糊时间默认取最新有效任务直接查，**禁止向用户反问**（单轮评测反问=0 分），答复中注明实际使用的任务时间即可。
- **最新任务可能很旧。** 预测系统不一定每天运行。先查 `SELECT taskid, tm, stuts FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1` 确认最新任务时间，若距今超过1天，需告知用户数据非实时。可降级查最近已完成任务(stuts = '1')。
- **查已完成任务。** 用 `WHERE stuts = '1' ORDER BY tm DESC` 过滤，避免拿到未完成的空任务。
- **最新已完成任务在子表中可能无数据（必读，0行必回退）。** 断面表 st_mx_rv_dm_r / 预测表 st_mx_preset_cal_r 只覆盖部分任务。若按"最新任务 taskid"过滤返回 0 行，**禁止直接放弃**，必须改用 EXISTS 回退到"有数据的最新任务"：
  ```sql
  SELECT t.taskid FROM slztk.st_mx_taskid_r t
  WHERE t.stuts = '1'
    AND EXISTS (SELECT 1 FROM slztk.st_mx_rv_dm_r d WHERE d.taskid = t.taskid)
  ORDER BY t.tm DESC LIMIT 1
  ```
  （查预测数据时把 EXISTS 里的表换成 st_mx_preset_cal_r。）取到该 taskid 后重新执行原查询，并在答复中说明实际使用的任务时间。

## Workflow

1. **获取最新任务 ID。** `SELECT taskid FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1`
2. **查询预测数据。** 用 taskid 过滤 st_mx_preset_cal_r，type='1' 为水位。**步骤 1-2（含时效检查与 EXISTS 回退）在同一个 Python 脚本内一轮完成**，f-string 实值代入。
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
- [ ] **降级策略**：若最新任务未完成(stuts = '0')，可降级查询最近已完成任务(stuts = '1')

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
- **任务状态:** stuts 是 char(1)，`stuts = '0'` 未完成, `stuts = '1'` 已完成（必须带引号）

## Related Skills

- `water-situation` — 实时水位查询
- `water-warning` — 防洪预警
- `water-visualization` — 预测 vs 实际水位对比图

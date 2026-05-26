---
name: water-quality
description: "水质综合查询 — 水质指标监测、水质等级评定（单因子评价法）、水质预测。核心表: sl325.wq_pcp_d, slztk.st_mx_preset_r_shj_auto, slztk.st_mx_taskid_shj_auto, slztk.wq_cod_pz, sl323.st_stbprp_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, quality, water-quality, monitoring, rating, forecast, CODMn, DO, NH3N, TP]
    category: water-resources
---

# 水质综合查询 (Water Quality)

查询水质监测指标、水质等级评定、水质预测。涉及 **三个库**: sl325(监测), slztk(预测), sl323(测站)。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询某测站水质指标（DO、CODMn、NH3N、TP、pH等） | Yes |
| 查询水质变化趋势 | Yes |
| 查询水质等级评定（单因子评价法） | Yes |
| 查询未来24小时水质预测及评级 | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，涉及三个库（只读）
  - sl325: wq_pcp_d（水质监测数据）
  - slztk: st_mx_preset_r_shj_auto, st_mx_taskid_shj_auto, wq_cod_pz（水质预测）
  - sl323: st_stbprp_b（测站信息）
- **pymysql:** execute_code 环境可能未安装，首次使用需先运行 `pip install pymysql`
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）

## Workflow

1. **识别查询场景。** 历史监测→sl325.wq_pcp_d; 等级评定→CASE WHEN 6级标准; 水质预测→slztk.st_mx_preset_r_shj_auto。
2. **识别水质站。** sttp='WQ'，通过 stnm LIKE 匹配站点。
3. **水质评级。** 按 6 级标准（Ⅰ~劣Ⅴ）对各指标分级，取最差等级。
4. **水质预测。** 获取最新 taskid，type 映射（103=DO, 104=CODMn, 105=TP, 128=NH3N）。
5. **跨库查询需带库名前缀:** sl325.wq_pcp_d, slztk.st_mx_preset_r_shj_auto 等。
6. **质量自检。** 执行 SQL 前确认符合安全规则。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。返回数值做合理性检查（CODMn 0~50mg/L, DO 0~20mg/L）。

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl325.wq_pcp_d | 水质监测 | stcd, **spt**(采样时间,PK), dox, codmn, nh3n, tp, ph, wtmp, turb, cond |
| slztk.st_mx_preset_r_shj_auto | 水质预测 | stcd, tm, **type**(int: 103/104/105/128), vals, taskid |
| slztk.st_mx_taskid_shj_auto | 水质预测任务 | **taskid**(PK), tm, **state**(0/1) |
| slztk.wq_cod_pz | CODMn转换 | min, max, **value**(decimal归一化值) |
| sl323.st_stbprp_b | 测站信息 | sttp='WQ' |

## Business Rules Summary

- **wq_pcp_d 时间字段是 spt**，不是 tm
- **水质站类型:** sttp='WQ'
- **st_mx_preset_r_shj_auto.type 是 int**，不是 varchar
- **st_mx_taskid_shj_auto 状态字段是 state**，不是 stuts
- **wq_cod_pz.value 是 decimal 归一化值**（0~100），不是等级名称
- **跨库查询:** wq_pcp_d 在 sl325，预测表在 slztk，测站表在 sl323

## Related Skills

- `water-warning` — 水质预警
- `water-situation` — 水位查询
- `water-visualization` — 水质指标趋势图、等级阶梯图

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
- 参考 `shared/statistical_methods.md` — 统计分析方法（趋势分析、异常检测、描述统计）
- 参考 `shared/sql_patterns.md` — SQL 通用查询模式（窗口函数、CTE 分步构建）
- 参考 `shared/analysis_validation.md` — 分析验证（质量检查清单、常见陷阱、置信度评定）

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

1. **识别查询场景。** 历史监测→sl325.wq_pcp_d; 等级评定→CASE WHEN 6级标准; 水质预测→slztk.st_mx_preset_r_shj_auto。
2. **识别水质站。** sttp='WQ'，通过 stnm LIKE 匹配站点。
3. **水质评级。** 按 6 级标准（Ⅰ~劣Ⅴ）对各指标分级，取最差等级。
4. **水质预测。** 获取最新 taskid，type 映射（103=DO, 104=CODMn, 105=TP, 128=NH3N）。
5. **跨库查询需带库名前缀:** sl325.wq_pcp_d, slztk.st_mx_preset_r_shj_auto 等。
6. **质量自检。** 执行 SQL 前确认符合安全规则。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。返回数值做合理性检查（CODMn 0~50mg/L, DO 0~20mg/L）。
7. **统计增强（可选）。** 如需趋势分析或异常检测，参考 shared/statistical_methods.md（移动平均、IQR 异常检测、水质指标分布描述）。
8. **输出验证。** 交付前按 shared/analysis_validation.md 做置信度评定——特别是同比/环比结论的陷阱检查（不完整周期、分母漂移、均值之均值）。

## Validation Gate

**水质查询交付前必须通过以下检查。**

### 水质评级检查

- [ ] **取最差等级**：单因子评价法必须取**最差等级**，不能取平均或多数等级
- [ ] **6 级标准正确性**：Ⅰ~劣Ⅴ 的划分阈值符合国标（GB 3838-2002）

**常见错误示例**：
```sql
❌ 错误：取出现次数最多的等级（多数原则）
✅ 正确：取最差等级（任一指标最差决定整体等级）
```

### 测站类型检查

- [ ] **水质站过滤正确**：sttp='WQ'，不能与水位站（ZZ）/水文站（ZQ）/水库站（RR）混淆
- [ ] **跨库 JOIN 测站类型验证**：JOIN sl323.st_stbprp_b 后确认 sttp='WQ'

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

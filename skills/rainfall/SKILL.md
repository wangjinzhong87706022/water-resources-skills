---
name: rainfall
description: "雨情综合查询 — 实时降雨、降雨预报（短临/中长期）、区域降雨统计。核心表: sl323.st_pptn_r, sl323.f_rnfl_h, sl323.f_rnfl_info_r, sl323.st_stbprp_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, rainfall, precipitation, forecast, hydrology, scada]
    category: water-resources
---

# 雨情综合查询 (Rainfall)

查询实时降雨量、降雨预报、区域降雨统计。数据源: MySQL 192.168.100.103:3306/sl323。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询某测站/区域实时降雨量 | Yes |
| 查询扬州城区降雨总量（固定 stcd='58245'） | Yes |
| 查询最大降雨日期 | Yes |
| 查询未来降雨预报（短临/中长期） | Yes |
| 查询各区域累计降雨量排名 | Yes |
| 查询某测站最近N天降雨数据 | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，数据库 sl323（只读）
- **pymysql:** execute_code 环境可能未安装，首次使用需先运行 `pip install pymysql`
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
- 参考 `references/schema.md` — 完整表结构（来源: 实际 MySQL DDL）
- 参考 `references/business_rules.md` — 业务规则（来源: domains/evidens.txt）
- 参考 `references/few_shots.md` — SQL 示例（来源: domains/sqls.txt）
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）

## Workflow

1. **识别查询场景。** 实时降雨→st_pptn_r; 降雨预报→f_rnfl_h; 区域统计→st_pptn_r + GROUP BY addvcd。
2. **识别实体和时间。** 扬州城区固定 stcd='58245'。
3. **生成 SQL。** JOIN st_stbprp_b 获取测站/区域信息。
4. **预报场景。** f_rnfl_h JOIN f_rnfl_info_r，过滤 UNITNAME='2' AND TYPE='2'，取最新 FYMDH。降雨量字段是 **RN** 不是 f_rnfl。
5. **质量自检。** 执行 SQL 前确认符合安全规则。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。返回数值做合理性检查（日降雨量 0~500mm）。
6. **输出格式。** 即使结果简单（如"今日无降雨"），也应包含：查询时间范围、测站名称(stnm)、数值结果、数据单位(mm)、简要说明。不要只回复一句话，应完整呈现查询上下文和结果含义。

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl323.st_pptn_r | 降雨量 | stcd, tm(PK), drp(时段降水量), dyp(日降水量) |
| sl323.f_rnfl_h | 降雨预报 | ID(网格码), FYMDH(发布时间), YMDH(预报时间), **RN**(降雨量), UNITNAME, TYPE |
| sl323.f_rnfl_info_r | 网格信息 | id(网格码), adcd_name, adcd_code |
| sl323.st_stbprp_b | 测站信息 | sttp='PP' 为雨量站 |

## Business Rules Summary

- **扬州城区:** 固定 stcd='58245'
- **短临预报过滤:** UNITNAME='2'(扬州气象) AND TYPE='2'(短临)
- **降雨量字段:** f_rnfl_h 中是 **RN**，不是 f_rnfl
- **网格关联:** f_rnfl_h.ID = f_rnfl_info_r.id
- **drp vs dyp:** drp=时段降水量, dyp=日降水量

## Related Skills

- `water-situation` — 水位查询（降雨影响水位）
- `water-warning` — 防洪预警
- `water-visualization` — 降雨量柱状图、月度对比图

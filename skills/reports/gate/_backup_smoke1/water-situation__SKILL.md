---
name: water-situation
description: "水情综合查询 — 河道水位、水库水位、防洪指标、超警戒判断。核心表: sl323.st_river_r, sl323.st_rsvr_r, sl323.st_stbprp_b, sl323.st_rvfcch_b。"
version: 2.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, river, reservoir, water-level, flood-control, hydrology, scada]
    category: water-resources
---

# 水情综合查询 (Water Situation)

查询河道/水库水位、防洪指标、超警戒判断。数据源: MySQL 192.168.100.103:3306/sl323。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询某河道实时/历史水位 | Yes |
| 查询水位是否超过警戒水位/保证水位 | Yes |
| 查询月度/年度水位统计（均值、最高、最低） | Yes |
| 查询重点河道水位（古运河、新城河、瘦西湖等） | Yes |
| 查询水库库水位、入库/出库流量、蓄水量 | Yes |
| 查询各站防洪指标（警戒水位、保证水位） | Yes |
| 水位趋势分析（涨/落/平） | Yes |

## Prerequisites

- **数据库:** MySQL 192.168.100.103:3306，数据库 sl323（只读）
- **连接:** pymysql, host='192.168.100.103', port=3306, user='root', password='<SL323_DB_PASSWORD>', database='sl323'
- **pymysql:** execute_code 环境可能未安装，首次使用需先运行 `pip install pymysql`
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。**不要手写 pymysql 连接代码。**
- 参考 `references/schema.md` — 完整表结构（来源: 实际 MySQL DDL）
- 参考 `references/business_rules.md` — 业务规则（来源: domains/evidens.txt）
- 参考 `references/few_shots.md` — SQL 示例（来源: domains/sqls.txt）
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则（所有 skill 通用）
- 参考 `shared/sql_quality_check.md` — SQL 质量审查流程（所有 skill 通用）

## Workflow

1. **识别查询场景。** 河道水位→st_river_r; 水库水位→st_rsvr_r; 防洪指标→st_rvfcch_b。
2. **识别测站/河道实体。** 参照重点河道映射（business_rules.md）。
3. **确定时间范围。** "实时/最新"→MAX(tm); "某天左右"→前后3天; "最近"→3天; "当前"→10天。
4. **生成 SQL。** JOIN st_stbprp_b 获取名称，LEFT JOIN st_rvfcch_b 获取警戒/保证水位。
5. **超警戒判断。** z > WRZ→超警戒; z > GRZ→超保证。
6. **水位保留两位小数。**
7. **质量自检。** 执行 SQL 前确认符合安全规则（只读、有 WHERE、有 LIMIT）。结果为空时按 shared/sql_quality_check.md Step 3 策略重试。返回数值做合理性检查（水位 -1~20m）。

## Key Tables

| 库.表 | 用途 | 关键列 |
|-------|------|--------|
| sl323.st_river_r | 河道水情 | stcd, tm(PK), z(水位), q(流量), wptn(水势) |
| sl323.st_rsvr_r | 水库水情 | stcd, tm(PK), rz(库水位), inq(入库), otq(出库), w(蓄水量), blrz(库下水位) |
| sl323.st_stbprp_b | 测站基础信息 | stcd, sttp(PK), stnm(名称), rvnm(河名) |
| sl323.st_rvfcch_b | 防洪指标 | STCD(无索引), WRZ(警戒), GRZ(保证), OBHTZ(实测最高) |

## Business Rules Summary

- **水势编码:** wptn 4=涨, 5=落, 6=平
- **测站类型:** ZZ=水位站, ZQ=水文站, RR=水库站
- **st_stbprp_b PK 是 (stcd, sttp)** 不是单独 stcd
- **st_rvfcch_b 无 PK**，STCD 上只有 INDEX
- **重点河道映射:** 详见 business_rules.md

## Related Skills

- `water-forecast` — 未来水位预测
- `water-warning` — 防洪预警判断
- `rainfall` — 降雨量查询（水位变化的关联因素）
- `water-visualization` — 水位趋势图、对比图

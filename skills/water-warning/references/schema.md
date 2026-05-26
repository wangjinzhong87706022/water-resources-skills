# 水利预警 Schema

> 来源: 实际 MySQL DDL (192.168.100.103)

## sl323.st_river_r — 河道水情表

（见 water-situation/references/schema.md）

## sl323.st_rvfcch_b — 河道站防洪指标表

| 字段 | 类型 | 含义 |
|------|------|------|
| STCD | varchar(18) NOT NULL | 测站编码 |
| LDKEL | decimal(7,3) | 左堤高程（m） |
| RDKEL | decimal(7,3) | 右堤高程（m） |
| WRZ | decimal(7,3) | 警戒水位（m） |
| WRQ | decimal(9,3) | 警戒流量（m³/s） |
| GRZ | decimal(7,3) | 保证水位（m） |
| GRQ | decimal(9,3) | 保证流量（m³/s） |
| FLPQ | decimal(9,3) | 平滩流量（m³/s） |
| OBHTZ | decimal(7,3) | 实测最高水位（m） |
| OBHTZTM | datetime | 实测最高水位出现时间 |
| IVHZ | decimal(7,3) | 调查最高水位（m） |
| IVHZTM | datetime | 调查最高水位出现时间 |
| OBMXQ | decimal(9,3) | 实测最大流量（m³/s） |
| OBMXQTM | datetime | 实测最大流量出现时间 |
| IVMXQ | decimal(9,3) | 调查最大流量（m³/s） |
| IVMXQTM | datetime | 调查最大流量出现时间 |
| HMXS | decimal(9,3) | 历史最大含沙量（kg/m³） |
| HMXSTM | datetime | 历史最大含沙量出现时间 |
| HMXAVV | decimal(9,3) | 历史最大断面平均流速（m/s） |
| HMXAVVTM | datetime | 历史最大断面平均流速出现时间 |
| HLZ | decimal(7,3) | 历史最低水位（m） |
| HLZTM | datetime | 历史最低水位出现时间 |
| HMNQ | decimal(9,3) | 历史最小流量（m³/s） |
| HMNQTM | datetime | 历史最小流量出现时间 |
| TAZ | decimal(7,3) | 高水位告警值（m） |
| TAQ | decimal(9,3) | 大流量告警值（m³/s） |
| LAZ | decimal(7,3) | 低水位告警值（m） |
| LAQ | decimal(9,3) | 小流量告警值（m³/s） |
| SFZ | decimal(7,3) | 启动预报水位标准（m） |
| SFQ | decimal(9,3) | 启动预报流量标准（m³/s） |
| MODITIME | datetime | 时间戳 |
| MAIN_RV | varchar(255) | 关联河道中重要河道 |
| EXTEND_STTP | char(2) | 扩展字段-类型 |
| EXTEND_STSW | decimal(9,3) | 扩展字段-生态水位 |
| EXTEND_UWRZ | varchar(255) | 扩展字段-闸上警戒水位 |
| EXTEND_DWRZ | varchar(255) | 扩展字段-闸下警戒水位 |

**无 PK** — STCD 不是主键
**注意:** STCD 列名是大写（不是小写 stcd），JOIN 时需写 `rv.STCD`

## sl325.wq_pcp_d — 水质监测数据表

（见 water-quality/references/schema.md）

**注意:** 时间字段是 **spt**（不是 tm）

## sl323.st_stbprp_b — 测站基础信息表

（见 water-situation/references/schema.md）

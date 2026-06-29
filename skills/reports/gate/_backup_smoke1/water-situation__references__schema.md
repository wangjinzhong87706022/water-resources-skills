# 水情 Schema

> 来源: 实际 MySQL DDL (192.168.100.103)

## sl323.st_river_r — 河道水情表

按时间 RANGE 分区 (p2023~p2026)

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (PK) |
| tm | datetime NOT NULL | 时间 (PK) |
| z | decimal(38,3) | 水位 (m) |
| q | decimal(38,3) | 流量 (m³/s) |
| xsa | decimal(38,3) | 断面过水面积 |
| xsavv | decimal(38,3) | 断面平均流速 |
| xsmxv | decimal(38,3) | 断面最大流速 |
| flwchrcd | char(1) | 河水特征码 |
| wptn | char(1) | 水势: 4=涨, 5=落, 6=平 |
| msqmt | char(1) | 测流方法 |
| msamt | char(1) | 测积方法 |
| msvmt | char(1) | 测速方法 |

**PK:** (stcd, tm)

## sl323.st_rsvr_r — 水库水情表

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(8) NOT NULL | 测站编码 (PK) |
| tm | datetime NOT NULL | 时间 (PK) |
| rz | decimal(7,3) | 库上水位 (m) |
| inq | decimal(9,3) | 入库流量 (m³/s) |
| w | decimal(9,3) | 蓄水量 (10⁶ m³) |
| blrz | decimal(7,3) | 库下水位 (m) |
| otq | decimal(9,3) | 出库流量 (m³/s) |
| rwchrcd | char(1) | 库水特征码 |
| rwptn | char(1) | 库水水势: 4=涨, 5=落, 6=平 |
| inqdr | decimal(5,2) | 入流时段长 |
| msqmt | char(1) | 测流方法 |

**PK:** (tm, stcd)

## sl323.st_stbprp_b — 测站基础信息表

共 34 个字段，以下为核心字段：

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (PK) |
| stnm | char(30) | 测站名称 |
| rvnm | char(30) | 河流名称 |
| hnnm | char(30) | 水系名称 |
| bsnm | char(30) | 流域名称 |
| lgtd | decimal(10,6) | 经度 |
| lttd | decimal(10,6) | 纬度 |
| stlc | char(50) | 站址 |
| addvcd | char(6) | 行政区划码 |
| sttp | char(2) NOT NULL | 站类 (PK): DD=闸, DP=泵, WQ=水质, ZZ=水位, ZQ=水文, PP=雨量, RR=水库 |
| frgrd | char(1) | 报讯等级 |
| esstym | char(6) | 建站年月 |
| usfl | char(1) | 启用标志: 1=启用, 0=停用 |
| source | char(1) | 数据来源: 1=自建, 2=气象, 3=水文, 4=环保, 5=邗江区站点 |
| gateheight | decimal(7,3) | 闸门高度 (m) |

**PK:** (stcd, sttp)

完整字段还包括: dtmnm, dtmel, dtpr, bgfrym, atcunit, admauth, locality, stbk, stazt, dstrvm, drna, phcd, comments, moditime, extend_rain_sort, extend_stcd_sort, extend_prst, extend_gate_sort, extend_wq_type

## sl323.st_rvfcch_b — 河道站防洪指标表

共 36 个字段，以下为核心字段：

| 字段 | 类型 | 含义 |
|------|------|------|
| STCD | varchar(18) NOT NULL | 测站编码 (INDEX, 非PK) |
| WRZ | decimal(7,3) | 警戒水位 (m) |
| GRZ | decimal(7,3) | 保证水位 (m) |
| WRQ | decimal(9,3) | 警戒流量 (m³/s) |
| GRQ | decimal(9,3) | 保证流量 (m³/s) |
| OBHTZ | decimal(7,3) | 实测最高水位 (m) |
| OBHTZTM | datetime | 实测最高水位出现时间 |
| HLZ | decimal(7,3) | 历史最低水位 (m) |
| HLZTM | datetime | 历史最低水位出现时间 |
| MAIN_RV | varchar(255) | 关联河道中重要河道 |
| EXTEND_STSW | decimal(9,3) | 生态水位 |
| EXTEND_UWRZ | varchar(255) | 闸上警戒水位 |
| EXTEND_DWRZ | varchar(255) | 闸下警戒水位 |

**无 PRIMARY KEY，无任何 INDEX** — 所有 JOIN 均为全表扫描

完整字段还包括: LDKEL, RDKEL, FLPQ, IVHZ, IVHZTM, OBMXQ, OBMXQTM, IVMXQ, IVMXQTM, HMXS, HMXSTM, HMXAVV, HMXAVVTM, HMNQ, HMNQTM, TAZ, TAQ, LAZ, LAQ, SFZ, SFQ, MODITIME, EXTEND_STTP

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

共 34 个字段（2026-06-29 据库全列核实）：

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (PK) |
| stnm | char(30) | 测站名称 |
| rvnm | char(30) | 河流名称 |
| hnnm | char(30) | 水系名称 |
| bsnm | char(30) | 流域名称 |
| lgtd | decimal(10,6) | 经度 (°) |
| lttd | decimal(10,6) | 纬度 (°) |
| stlc | char(50) | 站址 |
| addvcd | char(6) | 行政区划码 |
| dtmnm | char(16) | 基面名称 |
| dtmel | decimal(7,3) | 基面高程 (m) |
| dtpr | decimal(7,3) | 基面修正值 (m) |
| sttp | char(2) NOT NULL | 站类 (PK): DD=闸, DP=泵, WQ=水质, ZZ=水位, ZQ=水文, PP=雨量, RR=水库 |
| frgrd | char(1) | 报讯等级 |
| esstym | char(6) | 建站年月 |
| bgfrym | char(6) | 始报年月 |
| atcunit | char(20) | 隶属行业单位 |
| admauth | char(20) | 信息管理单位 |
| locality | char(10) NOT NULL | 交换管理单位 |
| stbk | char(1) | 测站岸别 |
| stazt | decimal(65,30) | 测站方位 (°) |
| dstrvm | decimal(6,1) | 至河口距离 (km) |
| drna | decimal(65,30) | 集水面积 |
| phcd | char(6) | 拼音码 |
| usfl | char(1) | 启用标志: 1=启用, 0=停用 |
| comments | varchar(200) | 备注 |
| moditime | datetime | 时间戳 |
| source | char(1) | 数据来源: 1=自建, 2=气象, 3=水文, 4=环保, 5=邗江区站点 |
| extend_rain_sort | int(11) | 扩展-雨量站排序 |
| extend_stcd_sort | int(11) | 扩展-站点排序（北到南, 东到西） |
| extend_prst | char(1) | 扩展-工程状态: 1=在建, 2=已建 |
| extend_gate_sort | int(11) | 扩展-闸站排序 |
| extend_wq_type | int(11) | 扩展-水质站类型（库无注释） |
| gateheight | decimal(7,3) | 扩展-闸门高度 (m) |

**PK:** (stcd, sttp) — 注意不是单独 stcd

## sl323.st_rvfcch_b — 河道站防洪指标表

共 36 个字段（2026-06-29 据库全列核实）：

| 字段 | 类型 | 含义 |
|------|------|------|
| STCD | varchar(18) NOT NULL | 测站编码（注意大写） |
| LDKEL | decimal(7,3) | 左堤高程 (m) |
| RDKEL | decimal(7,3) | 右堤高程 (m) |
| WRZ | decimal(7,3) | 警戒水位 (m) |
| WRQ | decimal(9,3) | 警戒流量 (m³/s) |
| GRZ | decimal(7,3) | 保证水位 (m) |
| GRQ | decimal(9,3) | 保证流量 (m³/s) |
| FLPQ | decimal(9,3) | 平滩流量 (m³/s) |
| OBHTZ | decimal(7,3) | 实测最高水位 (m) |
| OBHTZTM | datetime | 实测最高水位出现时间 |
| IVHZ | decimal(7,3) | 调查最高水位 (m) |
| IVHZTM | datetime | 调查最高水位出现时间 |
| OBMXQ | decimal(9,3) | 实测最大流量 (m³/s) |
| OBMXQTM | datetime | 实测最大流量出现时间 |
| IVMXQ | decimal(9,3) | 调查最大流量 (m³/s) |
| IVMXQTM | datetime | 调查最大流量出现时间 |
| HMXS | decimal(9,3) | 历史最大含沙量 (kg/m³) |
| HMXSTM | datetime | 历史最大含沙量出现时间 |
| HMXAVV | decimal(9,3) | 历史最大断面平均流速 (m/s) |
| HMXAVVTM | datetime | 历史最大断面平均流速出现时间 |
| HLZ | decimal(7,3) | 历史最低水位 (m) |
| HLZTM | datetime | 历史最低水位出现时间 |
| HMNQ | decimal(9,3) | 历史最小流量 (m³/s) |
| HMNQTM | datetime | 历史最小流量出现时间 |
| TAZ | decimal(7,3) | 高水位告警值 (m) |
| TAQ | decimal(9,3) | 大流量告警值 (m³/s) |
| LAZ | decimal(7,3) | 低水位告警值 (m) |
| LAQ | decimal(9,3) | 小流量告警值 (m³/s) |
| SFZ | decimal(7,3) | 启动预报水位标准 (m) |
| SFQ | decimal(9,3) | 启动预报流量标准 (m³/s) |
| MODITIME | datetime | 时间戳 |
| MAIN_RV | varchar(255) | 关联河道中重要河道 |
| EXTEND_STTP | char(2) | 扩展字段-类型 |
| EXTEND_STSW | decimal(9,3) | 扩展字段-生态水位 |
| EXTEND_UWRZ | varchar(255) | 扩展字段-闸上警戒水位 |
| EXTEND_DWRZ | varchar(255) | 扩展字段-闸下警戒水位 |

**无 PRIMARY KEY；据 INFORMATION_SCHEMA 该表所有列均无索引（STCD 也无索引）** — 所有 JOIN 均为全表扫描。该表仅 231 行，全表扫描可接受。

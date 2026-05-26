# 闸泵工况 Schema

> 来源: 实际 MySQL DDL (192.168.100.103)

## sl323.st_gate_r — 闸门启闭情况表

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (**PK**) |
| tm | datetime NOT NULL | 时间 (**PK**) |
| gtname | char(18) NOT NULL | 闸门名称 (**PK**) |
| exkey | char(1) | 扩展关键字 |
| eqptp | char(2) | 设备类别 |
| eqpno | char(2) | 设备编号 |
| gtopnum | decimal(3,0) | 开启孔数 |
| gtophgt | decimal(8,2) | 开启高度（m），>0 表示已开启 |
| gto | decimal(9,3) | 过闸流量（m³/s） |
| msqmt | char(1) | 测流方法 |
| ua | decimal(11,1) | 相电压 UA（V） |
| ub | decimal(11,1) | 相电压 UB（V） |
| uc | decimal(11,1) | 相电压 UC（V） |
| ia | decimal(11,1) | 电流 IA（A） |
| ib | decimal(11,1) | 电流 IB（A） |
| ic | decimal(11,1) | 电流 IC（A） |
| ps | decimal(11,1) | 总有功功率（KW） |
| qd | decimal(11,1) | 总无功功率（KW） |
| fr | decimal(11,1) | 频率（Hz） |
| pf | decimal(11,1) | 功率因数 |
| uab | decimal(11,1) | 线电压 Uab（V） |
| ubc | decimal(11,1) | 线电压 Ubc（V） |
| uca | decimal(11,1) | 线电压 Uca（V） |
| open_state | char(1) | 全开状态 |
| close_state | char(1) | 全关状态 |

**PK:** (stcd, tm, gtname) — 一个测站可有多个闸门
**注意:** 此表**没有** upz/dwz 字段，上下游水位在 st_was_r 中

## sl323.st_was_r — 堰闸水情表

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (**PK**) |
| tm | datetime NOT NULL | 时间 (**PK**) |
| upz | decimal(7,3) | 闸上水位（m） |
| dwz | decimal(7,3) | 闸下水位（m） |
| tgtq | decimal(9,3) | 总过闸流量（m³/s） |
| swchrcd | char(1) | 闸水特征码 |
| supwptn | char(1) | 闸上水势 |
| sdwwptn | char(1) | 闸下水势 |
| msqmt | char(1) | 测流方法 |

**PK:** (tm, stcd) — 注意 tm 在前
**分区:** RANGE by tm，半年一个分区

## sl323.st_pump_r — 泵站水情表

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (**PK**) |
| tm | datetime NOT NULL | 时间 (**PK**) |
| ppupz | decimal(7,3) | 站上水位（m） |
| ppdwz | decimal(7,3) | 站下水位（m） |
| omcn | decimal(3,0) | 开机台数，>0 表示有泵运行 |
| ompwr | decimal(5,0) | 开机功率（kw） |
| pmpq | decimal(7,3) | 抽水流量（m³/s） |
| ppwchrcd | char(1) | 站水特征码 |
| ppupwptn | char(1) | 站上水势 |
| ppdwwptn | char(1) | 站下水势 |
| msqmt | char(1) | 测流方法 |
| pdchcd | char(1) | 引排特征码（'1'=引水, '2'=排水） |
| pumpname | char(18) | 泵名称 |

**PK:** (tm, stcd) — 注意 tm 在前，pumpname 不在 PK 中
**分区:** RANGE by tm，半年一个分区

## sl323.st_pump_pa — 泵站工情表

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (**PK**) |
| tm | datetime NOT NULL | 时间 (**PK**) |
| pumpname | char(18) NOT NULL | 设备名称 (**PK**) |
| switch | int(1) | 开关（1=开, 0=关） |
| ua | decimal(8,1) | 相电压 UA（V） |
| ub | decimal(8,1) | 相电压 UB（V） |
| uc | decimal(8,1) | 相电压 UC（V） |
| uab | decimal(8,1) | 线电压 Uab（V） |
| ubc | decimal(8,1) | 线电压 Ubc（V） |
| uca | decimal(8,1) | 线电压 Uca（V） |
| ia | decimal(8,1) | 电流 IA（A） |
| ib | decimal(8,1) | 电流 IB（A） |
| ic | decimal(8,1) | 电流 IC（A） |
| pa | decimal(8,1) | A 相有功功率（KW） |
| pb | decimal(8,1) | B 相有功功率（KW） |
| pc | decimal(8,1) | C 相有功功率（KW） |
| ps | decimal(8,1) | 总有功功率（KW） |
| qa | decimal(8,1) | A 相无功功率（KW） |
| qb | decimal(8,1) | B 相无功功率（KW） |
| qc | decimal(8,1) | C 相无功功率（KW） |
| qd | decimal(8,1) | 总无功功率（KW） |
| ss | decimal(8,1) | 总视在功率（KW） |
| pf | decimal(8,1) | 总功率因数 |
| fr | decimal(8,1) | 频率（Hz） |
| ta | decimal(8,1) | A 相温度（℃） |
| tb | decimal(8,1) | B 相温度（℃） |
| tc | decimal(8,1) | C 相温度（℃） |
| bak1 | varchar(255) | 备用字段 1 |
| bak2 | varchar(255) | 备用字段 2 |
| bak3 | varchar(255) | 备用字段 3 |

**PK:** (stcd, tm, pumpname) — pumpname 在 PK 中（与 st_pump_r 不同）
**分区:** RANGE by tm，按月分区

## sl323.st_stbprp_b — 测站基础信息表

（见 water-situation/references/schema.md）

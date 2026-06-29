# 水质 Schema

> 来源: 实际 MySQL DDL (192.168.100.103)

## sl325.wq_pcp_d — 水质数据表

共 **45** 个字段（2026-06-29 据库核实，旧文档"43"有误）：

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(20) NOT NULL | 测站编码 (PK) |
| prpnm | char(1) | 垂线编号 |
| ltnm | char(1) | 层面编号 |
| **spt** | **datetime NOT NULL** | **采样时间 (PK)** — 注意不是 tm |
| dox | decimal(10,1) | 溶解氧 DO (mg/L) |
| codmn | decimal(10,1) | 高锰酸盐指数 CODMn (mg/L) |
| codcr | decimal(10,1) | 化学需氧量 CODCr (mg/L) |
| bod5 | decimal(10,1) | 五日生化需氧量 BOD5 (mg/L) |
| wtmp | decimal(10,1) | 水温 (℃) |
| ph | decimal(10,2) | pH 值 |
| cond | decimal(10,2) | 电导率 (μS/cm) |
| redox | decimal(10,1) | 氧化还原电位 (mV) |
| nh3n | decimal(10,2) | 氨氮 NH3-N (mg/L) |
| tn | decimal(10,2) | 总氮 TN (mg/L) |
| cu | decimal(10,4) | 铜 (mg/L) |
| turb | decimal(10,2) | 浊度 (mg/L) |
| zn | decimal(10,4) | 锌 (mg/L) |
| f | decimal(10,2) | 氟化物 (mg/L) |
| se | decimal(10,5) | 硒 (mg/L) |
| ars | decimal(10,5) | 砷 (mg/L) |
| hg | decimal(10,5) | 汞 (mg/L) |
| cd | decimal(10,5) | 镉 (mg/L) |
| cr6 | decimal(10,3) | 六价铬 (mg/L) |
| pb | decimal(10,5) | 铅 (mg/L) |
| cn | decimal(10,3) | 氰化物 (mg/L) |
| vlph | decimal(10,3) | 挥发酚 (mg/L) |
| benf | decimal(10,2) | 苯酚 (mg/L) |
| s2 | decimal(10,3) | 硫化物 (mg/L) |
| fcg | decimal(10,0) | 粪大肠菌群 (mg/L) |
| so4 | decimal(10,2) | 硫酸盐 (mg/L) |
| cl | decimal(10,2) | 氯化物 (mg/L) |
| no3 | decimal(10,2) | 硝酸盐氮 (mg/L) |
| fe | decimal(10,2) | 铁 (mg/L) |
| mn | decimal(10,2) | 锰 (mg/L) |
| oil | decimal(10,2) | 石油类 (mg/L) |
| las | decimal(10,2) | 阴离子表面活性剂 (mg/L) |
| bhc | decimal(10,6) | 六六六 (mg/L) |
| ddt | decimal(10,6) | 滴滴涕 (mg/L) |
| ope | decimal(10,6) | 有机氯农药 (mg/L) |
| tp | decimal(10,2) | 总磷 TP (mg/L) |
| chla | decimal(10,2) | 叶绿素 a (mg/L) |
| ts | decimal(10,2) | 总悬浮物 (mg/L) |
| bak1 | varchar(255) | 备用字段 1 |
| bak2 | varchar(255) | 备用字段 2 |
| bak3 | varchar(255) | 备用字段 3 |

**PK:** (stcd, spt) — 时间字段名是 **spt**，不是 tm

## slztk.st_mx_preset_r_shj_auto — 水质预测结果表

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | varchar(18) NOT NULL | 测站编码 (INDEX) |
| tm | datetime NOT NULL | 监测时间 |
| type | **int(5)** | 数据类型: 1=水位, 2=流量, 24=入流, 33=净雨量, 35=径流量, 103=DO浓度, 104=COD浓度, 105=TP, 128=NH3N |
| vals | double(8,3) | 预测值 |
| stnm | varchar(255) | 测站名称/描述 |
| taskid | varchar(50) | 任务 ID (INDEX) |
| ts | datetime | 时间戳 |

**索引:** stcd / type / taskid 上各有一个普通索引（据 INFORMATION_SCHEMA，未见 PRIMARY/UNIQUE；唯一性以 `SHOW INDEX` 为准）
**注意:** type 是 **int** 类型，不是 varchar

## slztk.st_mx_taskid_shj_auto — 水质预测任务表

| 字段 | 类型 | 含义 |
|------|------|------|
| taskid | varchar(18) NOT NULL | 任务 ID (PK) |
| tm | datetime | 调度开始时间 |
| parm_json | json | 入参 |
| user | varchar(255) | 编制人员 |
| step | varchar(255) | 步长 |
| task_name | varchar(255) | 任务名称 |
| ts | datetime | 时间戳 |
| type | char(1) | 任务类型: 1=定时任务, 2=计算任务 |
| **state** | **char(1)** | 计算状态: 0=未完成, 1=完成 — 注意字段名是 state 不是 stuts |
| endTm | varchar(255) | 结束时间 |
| task_des | varchar(2000) | 任务描述 |
| obj_json | json | 调度对象 |
| planid | varchar(50) | 预案 ID |
| ddtype | char(255) | 调度类型: 1=目标调度, 2=基本调度 |
| ip | varchar(255) | 调度来源 IP |
| isDel | char(1) | 是否删除 |

**PK:** (taskid)

## slztk.wq_cod_pz — CODMn 归一化转换表

| 字段 | 类型 | 含义 |
|------|------|------|
| min | decimal(8,2) | 最小值 |
| max | decimal(8,2) | 最大值 |
| value | decimal(8,2) | 归一化转换值 (0~100 数值) |

**无 PK**

**注意:** value 是 **decimal 数值**（0.00~100.00 的归一化值），不是等级名称。用于将模型输出的 CODMn 原始值转换为标准化的数值。

## sl323.st_stbprp_b — 测站基础信息表

（见 water-situation/references/schema.md）

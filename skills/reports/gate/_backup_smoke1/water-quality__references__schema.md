# 水质 Schema

> 来源: 实际 MySQL DDL (192.168.100.103)

## sl325.wq_pcp_d — 水质数据表

共 43 个字段，以下为核心字段：

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(20) NOT NULL | 测站编码 (PK) |
| prpnm | char(1) | 垂线编号 |
| ltnm | char(1) | 层面编号 |
| **spt** | **datetime NOT NULL** | **采样时间 (PK)** — 注意不是 tm |
| dox | decimal(10,1) | 溶解氧 DO (mg/L) |
| codmn | decimal(10,1) | 高锰酸盐指数 CODMn (mg/L) |
| wtmp | decimal(10,1) | 水温 (℃) |
| ph | decimal(10,2) | pH 值 |
| cond | decimal(10,2) | 电导率 (μS/cm) |
| nh3n | decimal(10,2) | 氨氮 NH3N (mg/L) |
| turb | decimal(10,2) | 浊度 (mg/L) |
| tp | decimal(10,2) | 总磷 TP (mg/L) |

**PK:** (stcd, spt) — 时间字段名是 **spt**，不是 tm

完整字段还包括: codcr, bod5, redox, tn, cu, zn, f, se, ars, hg, cd, cr6, pb, cn, vlph, benf, s2, fcg, so4, cl, no3, fe, mn, oil, las, bhc, ddt, ope, chla, ts, bak1-3

## slztk.st_mx_preset_r_shj_auto — 水质预测结果表

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | varchar(18) NOT NULL | 测站编码 |
| tm | datetime NOT NULL | 预报时间 |
| type | **int(5)** | 参数类型: 103=DO, 104=CODMn, 105=TP, 128=NH3N |
| vals | double(8,3) | 预报值 |
| stnm | varchar(255) | 测站名称 |
| taskid | varchar(50) | 任务 ID |

**UNIQUE KEY:** (stcd, tm, type, stnm, taskid)

**注意:** type 是 **int** 类型，不是 varchar

## slztk.st_mx_taskid_shj_auto — 水质预测任务表

| 字段 | 类型 | 含义 |
|------|------|------|
| taskid | varchar(18) NOT NULL | 任务 ID (PK) |
| tm | datetime | 调度开始时间 |
| type | char(1) | 任务类型: 1=定时任务, 2=计算任务 |
| **state** | **char(1)** | 计算状态: 0=未完成, 1=完成 — 注意字段名是 state 不是 stuts |
| step | varchar(255) | 步长 |
| user | varchar(255) | 编制人员 |
| task_name | varchar(255) | 任务名称 |
| task_des | varchar(2000) | 任务描述 |
| ddtype | char(255) | 调度类型: 1=目标调度, 2=基本调度 |
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

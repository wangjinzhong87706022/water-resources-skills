# 水位预测 Schema

> 来源: 实际 MySQL DDL (192.168.100.103)

## slztk.st_mx_preset_cal_r — 存储调度结果数据（水位、雨量、闸位）

| 字段 | 类型 | 含义 |
|------|------|------|
| taskid | varchar(18) NOT NULL | 任务 ID (INDEX) |
| stcd | varchar(18) NOT NULL | 测站编码 |
| tm | datetime NOT NULL | 预报时间/预测时间 |
| type | **varchar(5)** | 数据类型: 1=水位, 2=流量, 3=闸门开启系数, 24=入流, 25=出流, 31=片区降雨, 33=净雨量, 35=片区径流量 |
| vals | double(8,3) | 预报结果/预测值 |
| stnm | varchar(255) | 测站名称 |
| step | varchar(255) | 步长 |
| ts | datetime | 时间戳 |

**无 PK**，有 INDEX(taskid), INDEX(stcd, tm), INDEX(vals, type)

**注意:** type 是 **varchar(5)** 不是 int，比较时应用引号: `type = '1'`

## slztk.st_mx_taskid_r — 调度计算过程记录表

| 字段 | 类型 | 含义 |
|------|------|------|
| uuid | char(36) NOT NULL | UUID (**PK**) |
| taskid | varchar(18) | 防洪任务 ID (INDEX) |
| nltaskid | varchar(18) | 内涝任务 ID |
| tm | datetime | 调度开始时间 |
| type | char(1) | 任务类型: 1=滚动预报, 2=模型计算 |
| stuts | char(1) | 0=计算未完成, 1=计算完成 |
| user | varchar(255) | 编制人员 |
| step | varchar(255) | 步长 |
| parm_json | json | 防洪输入参数 |
| result_json | json | 计算结果 json |
| task_name | varchar(255) | 任务名称 |
| endTm | datetime | 调度结束时间 |
| calTm | varchar(255) | 计算完成时间 |
| planid | varchar(30) | 预案 ID |

**PK:** (uuid) — **不是 taskid**，taskid 只是普通字段

## slztk.st_mx_rv_dm_r — 河道断面数据

| 字段 | 类型 | 含义 |
|------|------|------|
| id | char(9) NOT NULL | ID |
| code | varchar(10) | code |
| name | varchar(255) NOT NULL | 断面名称 |
| z | double(8,2) | 水位 z |
| Qin | double(8,2) | 入流 |
| Qout | double(8,2) | 出流 |
| tm | datetime NOT NULL | 时间 |
| taskid | varchar(18) | 任务 ID |

**无 PK**，有 INDEX(taskid), INDEX(id, code, tm, taskid, name)

## sl323.st_stbprp_b — 测站基础信息表

（见 water-situation/references/schema.md）

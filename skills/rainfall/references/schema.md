# 雨情 Schema

> 来源: 实际 MySQL DDL (192.168.100.103)

## sl323.st_pptn_r — 降雨量表

按时间 RANGE 分区 (p2023~p2026)

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (PK) |
| tm | datetime NOT NULL | 时间 (PK) |
| drp | decimal(5,1) | 时段降水量 (mm) |
| invt | decimal(5,2) | 时段长 (h) |
| pdr | decimal(5,2) | 降水历时 |
| dyp | decimal(5,1) | 日降水量 (mm) |
| wth | char(1) | 天气状况 |
| type | char(1) | 类型 (2=气象局) |

**PK:** (tm, stcd)

**注意:** drp 是时段降水量，dyp 是日降水量，业务含义不同。

## sl323.f_rnfl_h — 未来72小时逐小时降雨预报数据

按时间 RANGE 分区 (p2023~p2026)

| 字段 | 类型 | 含义 |
|------|------|------|
| ID | int(11) NOT NULL | 网格代码 (PK) |
| FYMDH | datetime NOT NULL | 发布时间 (PK) |
| YMDH | datetime NOT NULL | 预报时间/预报时刻 (PK) |
| RN | decimal(11,2) NOT NULL | 降水量/降雨量 (mm) |
| UNITNAME | varchar(255) NOT NULL | 发布单位 (PK): 1=和风天气, 2=扬州气象局, 3=扬州气象-新, 4=欧洲大数据中心, 9=备用, 99=其他 |
| COMMENTS | varchar(255) | 校正注解 |
| TYPE | varchar(255) NOT NULL | 预报类型 (PK): 1=未来3天每小时, 2=未来2小时每5分钟, 3=未来24小时每小时 |

**PK:** (ID, YMDH, UNITNAME, TYPE)

## sl323.f_rnfl_info_r — 行政区经纬度信息表

| 字段 | 类型 | 含义 |
|------|------|------|
| id | int(11) NOT NULL | 网格代码 (PK) |
| longitude | decimal(10,6) | 经度 |
| latitude | decimal(10,6) | 纬度 |
| adcd_name | varchar(255) | 行政区名称（如'扬州城区'） |
| adcd_code | varchar(255) NOT NULL | 行政区划代码（如'320188'）(PK) |

**PK:** (id, adcd_code)

## sl323.st_stbprp_b — 测站基础信息表

（见 water-situation/references/schema.md）

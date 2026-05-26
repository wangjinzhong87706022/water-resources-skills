# sl323.st_rvfcch_b — 河道站防洪指标表

> water-situation / water-warning / gate-pump-operation 共用。

## 核心字段

| 字段 | 类型 | 含义 |
|------|------|------|
| STCD | varchar(18) NOT NULL | 测站编码 (注意大写) |
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

## 关键注意事项

1. **无 PRIMARY KEY**，STCD 上只有 INDEX，所有 JOIN 均为全表扫描
2. **STCD 列名是大写**（不是小写 stcd），JOIN 时必须写 `rv.STCD`
3. JOIN 条件示例：`r.stcd = rv.STCD`（注意大小写混用）
4. 该表数据量较小（几十到几百条），全表扫描性能可接受

## 预警判断规则

| 条件 | 预警级别 |
|------|---------|
| z > WRZ 且 WRZ 不为 NULL | 黄色预警（超警戒） |
| z > GRZ 且 GRZ 不为 NULL | 红色预警（超保证） |
| z <= WRZ 或 WRZ 为 NULL | 正常 |

# 雨情业务规则

> 来源: /home/scada/dataagent/domains/evidens.txt 原文

## 扬州城区降雨量过滤

来源: evidens.txt "扬州城区降雨量过滤"

查询扬州城区降雨量时，必须添加过滤条件 `stcd = '58245'`。
同义词: 扬州市区降雨, 扬州降雨, 扬州雨量

## 短临降雨预报查询

来源: evidens.txt "短临降雨预测查询"

- 查询表: sl323.f_rnfl_h
- 固定过滤: UNITNAME = '2' (扬州气象) AND TYPE = '2' (短临)
- 扬州城区过滤: 在 f_rnfl_info_r 中添加 WHERE adcd_name='扬州城区' 或 adcd_code='320188'
- 发布时间 FYMDH 需取最新: `ORDER BY FYMDH DESC LIMIT 1`
- 降雨量字段名: **RN**（不是 f_rnfl）

## 短临降雨关联逻辑

来源: evidens.txt "短临降雨关联逻辑"

必须关联网格信息表:
```sql
FROM f_rnfl_h JOIN f_rnfl_info_r ON f_rnfl_info_r.id = f_rnfl_h.ID
```
关联键为网格代码 (ID)。

## 区域降雨量统计逻辑

来源: evidens.txt "区域降雨量统计逻辑"

统计步骤:
1. 基础单元: st_stbprp_b.stcd 对应 st_stbprp_b.addvcd
2. 计算逻辑:
   - 第一步: 按测站+区域分组统计降雨总量 SUM(drp)
   - 第二步: 按区域分组计算该区域内所有测站累计降雨量的平均值 AVG()
3. 约束: addvcd IS NOT NULL AND addvcd != ''
4. 若仅统计雨量站: 需加 st_stbprp_b.sttp = 'PP'

## 时间范围定义

来源: evidens.txt "时间范围定义"

| 关键词 | 定义 |
|--------|------|
| 最近 | 当前时间的最近三天 |
| 最新/实时 | 数据库中最大时间值对应的记录 |
| 当前 | 最近10天数据 |

## 时段降水量 vs 日降水量

- **drp**: 时段降水量 (mm) — 某个时间段内的降水
- **dyp**: 日降水量 (mm) — 一整天的降水总量
- 查询"日降雨量"应使用 dyp 或 GROUP BY DATE(tm) SUM(drp)

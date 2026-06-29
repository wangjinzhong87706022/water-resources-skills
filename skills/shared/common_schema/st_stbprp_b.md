# sl323.st_stbprp_b — 测站基础信息表

> 6 个水利 skill 共用的测站主数据表。

## 全部字段（34 列，2026-06-29 据库核实）

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

## 测站类型 (sttp) 映射

| sttp | 含义 | 对应 Skill |
|------|------|-----------|
| ZZ | 水位站 | water-situation, water-warning |
| ZQ | 水文站 | water-situation |
| RR | 水库站 | water-situation |
| PP | 雨量站 | rainfall |
| DD | 闸站 | gate-pump-operation |
| DP | 泵站 | gate-pump-operation |
| WQ | 水质站 | water-quality, water-warning |

## 常用查询模式

```sql
-- 按河流查测站
SELECT stcd, stnm, sttp FROM sl323.st_stbprp_b WHERE rvnm LIKE '%古运河%' AND usfl = '1';

-- 按类型查测站
SELECT stcd, stnm, rvnm FROM sl323.st_stbprp_b WHERE sttp = 'ZZ' AND usfl = '1';

-- 模糊匹配站名
SELECT stcd, stnm, sttp, rvnm FROM sl323.st_stbprp_b WHERE stnm LIKE '%宝应%' AND usfl = '1';
```

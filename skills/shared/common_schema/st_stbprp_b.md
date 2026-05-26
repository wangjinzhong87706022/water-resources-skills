# sl323.st_stbprp_b — 测站基础信息表

> 6 个水利 skill 共用的测站主数据表。

## 核心字段

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
| sttp | char(2) NOT NULL | 站类 (PK) |
| frgrd | char(1) | 报讯等级 |
| esstym | char(6) | 建站年月 |
| usfl | char(1) | 启用标志: 1=启用, 0=停用 |
| source | char(1) | 数据来源: 1=自建, 2=气象, 3=水文, 4=环保, 5=邗江区站点 |
| gateheight | decimal(7,3) | 闸门高度 (m) |

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

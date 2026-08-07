# 水利预警 Few-Shot 示例

> ⚠️ **禁相关子查询求"每站最新"（30s 必超时），必须用派生表 JOIN（实测 0.1s）；相对时间窗锚 `MAX(tm)`，禁锚 NOW()/CURDATE()**（库数据滞后于挂钟）。

> 来源: /home/scada/dataagent/domains/sqls.txt 原始 Question-SQL 对

## 防洪预警

### Q: 扬州市重点河道水位实时情况（含超警戒判断）

```sql
SELECT b.stnm AS '测站名称', r.z AS '实时水位', r.tm AS '更新时间',
       rv.WRZ AS '警戒水位',
       CASE WHEN r.z > rv.WRZ THEN '是' ELSE '否' END AS '是否超警戒'
FROM sl323.st_river_r r
INNER JOIN (
  SELECT r.stcd, b.stnm, MAX(tm) AS maxTm
  FROM sl323.st_river_r r
  INNER JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
  WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）',
                    '七里河水位站（东花园路）', '赵家支沟水文站（赵家河路）', '瘦西湖水位站')
  GROUP BY r.stcd, b.stnm
) sub ON r.stcd = sub.stcd AND r.tm = sub.maxTm
INNER JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD;
```

**注意:**
- st_rvfcch_b.STCD 是**大写**
- 子查询别名用 `sub` 而非 `b`，避免与外层 st_stbprp_b 别名冲突

### Q: 24年8月20号左右，扬州古运河、新城河、瘦西湖最高水位及是否超标

```sql
SELECT b.stnm AS '测站名称', r.z AS '最高水位', r.tm AS '出现时间',
       rv.WRZ AS '警戒水位',
       CASE WHEN r.z > rv.WRZ THEN '是' ELSE '否' END AS '是否超标'
FROM sl323.st_river_r r
INNER JOIN (
  SELECT stcd, MAX(z) AS max_z
  FROM sl323.st_river_r
  WHERE tm BETWEEN '2024-08-17' AND '2024-08-23'
  GROUP BY stcd
) AS sub ON r.stcd = sub.stcd AND r.z = sub.max_z
INNER JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
INNER JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
WHERE r.tm BETWEEN '2024-08-17' AND '2024-08-23'
  AND b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）', '瘦西湖水位站')
ORDER BY b.stnm;
-- 注意：不能用 MAX(tm) 当"最高水位出现时间"——MAX(tm) 只是时段内最后一条记录的时刻。
-- 必须派生表求每站 max_z 后回表 JOIN 定位其 tm；若同一 max_z 出现在多个时刻会返回多行，可任取其一（如再包一层 MIN(tm)）。
```

### Q: 查询当前超警戒水位的站点

```sql
SELECT b.stnm AS '测站名称', r.z AS '当前水位', rv.WRZ AS '警戒水位',
       rv.GRZ AS '保证水位', r.tm AS '更新时间',
       CASE
         WHEN r.z > rv.GRZ THEN '红色预警（超保证）'
         WHEN r.z > rv.WRZ THEN '黄色预警（超警戒）'
         ELSE '正常'
       END AS '预警等级'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_river_r GROUP BY stcd) latest
  ON r.stcd = latest.stcd AND r.tm = latest.maxTm
WHERE r.z > rv.WRZ
ORDER BY r.z - rv.WRZ DESC;
```

### Q: 查询防洪预警汇总

```sql
SELECT
  COUNT(*) AS '监测站点总数',
  SUM(CASE WHEN r.z > rv.WRZ THEN 1 ELSE 0 END) AS '超警戒站点数',
  SUM(CASE WHEN r.z > rv.GRZ THEN 1 ELSE 0 END) AS '超保证站点数',
  SUM(CASE WHEN r.z <= rv.WRZ THEN 1 ELSE 0 END) AS '正常站点数'
FROM sl323.st_river_r r
JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_river_r GROUP BY stcd) latest
  ON r.stcd = latest.stcd AND r.tm = latest.maxTm;
```

## 水质预警

### Q: 查询水质低于Ⅳ类的站点

```sql
SELECT b.stnm AS '测站名称', d.spt AS '采样时间',
       d.codmn AS 'CODMn', d.dox AS 'DO', d.nh3n AS 'NH3N', d.tp AS 'TP',
       CASE
         WHEN d.codmn > 10 OR d.dox < 3 OR d.nh3n > 1.5 OR d.tp > 0.3 THEN '劣于Ⅳ类'
         ELSE '正常'
       END AS '预警状态'
FROM sl325.wq_pcp_d d
JOIN (SELECT stcd, MAX(spt) AS maxSpt FROM sl325.wq_pcp_d GROUP BY stcd) m
  ON d.stcd = m.stcd AND d.spt = m.maxSpt
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.sttp = 'WQ'
  AND (d.codmn > 10 OR d.dox < 3 OR d.nh3n > 1.5 OR d.tp > 0.3);
```

**注意:**
- wq_pcp_d 在 **sl325** 库，st_stbprp_b 在 **sl323** 库
- wq_pcp_d 时间字段是 **spt**（不是 tm）
- **严禁相关子查询 `d.spt = (SELECT MAX(spt) ... WHERE stcd = d.stcd)`**——实测 30s 必超时，必须如上用派生表 JOIN（实测 0.1s）

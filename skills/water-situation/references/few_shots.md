# 水情 Few-Shot 示例

> 来源: /home/scada/dataagent/domains/sqls.txt 原始 Question-SQL 对

## 河道水位

> ⚠️ **写 SQL 前先看这条反例。** 提到具体测站名(宝应/白马闸/古运河)时,**所有正确示例都用 `JOIN st_stbprp_b ... WHERE stnm LIKE '%站名%'` 按名直查**。**不要**写 `stcd='{stcd}'`、`DATE(tm)='{dt}'` 这种未填值的占位符——会匹配 0 行。时间窗用 `DATE_SUB(CURDATE(), INTERVAL N DAY/MONTH)`,不要写窄(30 天≠单天)。
>
> ❌ 错(占位符污染,0 行): `WHERE stcd='{stcd}' AND DATE(tm)='{dt}'`
> ✅ 对(按名 JOIN): `JOIN st_stbprp_b b ON r.stcd=b.stcd WHERE b.stnm LIKE '%宝应%' AND r.tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)`

### Q: 2024年古运河平均水位？

```sql
SELECT b.stnm AS 测站名称, AVG(r.z) AS 年平均水位
FROM st_river_r AS r
INNER JOIN st_stbprp_b AS b ON r.stcd = b.stcd
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
  AND r.tm BETWEEN '2024-01-01' AND '2024-12-31'
  AND r.z IS NOT NULL
GROUP BY b.stnm;
```

### Q: 新城河口2024年一年的水位情况？

```sql
SELECT b.stnm AS 测站名称,
       DATE_FORMAT(r.tm, '%Y-%m') AS 月份,
       AVG(r.z) AS 月平均水位, MAX(r.z) AS 月最高水位, MIN(r.z) AS 月最低水位
FROM st_river_r r
INNER JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%新城河口%'
  AND r.tm BETWEEN '2024-01-01' AND '2024-12-31'
  AND r.z IS NOT NULL
GROUP BY b.stnm, DATE_FORMAT(r.tm, '%Y-%m')
ORDER BY DATE_FORMAT(r.tm, '%Y-%m');
```

### Q: 扬州市重点河道水位实时情况

```sql
SELECT b.stnm AS 测站名称, r.z AS 实时水位, r.tm AS 更新时间,
       rv.WRZ AS 警戒水位,
       CASE WHEN r.z > rv.WRZ THEN '是' ELSE '否' END AS 是否超警戒
FROM st_river_r r
INNER JOIN (
  SELECT r.stcd, b.stnm, MAX(tm) AS maxTm
  FROM st_river_r r INNER JOIN st_stbprp_b b ON r.stcd = b.stcd
  WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）',
                    '七里河水位站（东花园路）', '赵家支沟水文站（赵家河路）', '瘦西湖水位站')
  GROUP BY r.stcd, b.stnm
) sub ON r.stcd = sub.stcd AND r.tm = sub.maxTm
INNER JOIN st_rvfcch_b rv ON r.stcd = rv.STCD;
```

### Q: 24年8月20号左右扬州古运河等最高水位，是否超排涝控制水位？

```sql
SELECT b.stnm AS 测站名称, sub.max_z AS 最高水位, sub.max_time AS 出现时间,
       rv.WRZ AS 警戒水位,
       CASE WHEN sub.max_z > rv.WRZ THEN '是' ELSE '否' END AS 是否超标
FROM st_stbprp_b b
INNER JOIN (
  SELECT stcd, MAX(z) AS max_z, MAX(tm) AS max_time
  FROM st_river_r WHERE tm BETWEEN '2024-08-17' AND '2024-08-23' GROUP BY stcd
) AS sub ON b.stcd = sub.stcd
INNER JOIN st_rvfcch_b rv ON b.stcd = rv.STCD
WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）', '瘦西湖水位站');
```

### Q: 水位站宝应最近30天水位数据

```sql
SELECT r.tm AS '时间', r.z AS '水位(m)'
FROM st_river_r r JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%宝应%'
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND r.z IS NOT NULL
ORDER BY r.tm;
```

### Q: 水位站白马闸的实时水位

```sql
SELECT r.tm AS '时间', r.z AS '水位(m)'
FROM st_river_r r JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm = '白马闸' AND r.z IS NOT NULL ORDER BY r.tm LIMIT 1;
```

### Q: 查询2025年古运河水位站点的数量

```sql
SELECT COUNT(DISTINCT r.stcd) AS 水位站点数量
FROM st_river_r r JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE b.sttp = 'ZZ' AND r.tm >= '2025-01-01' AND r.tm < '2026-01-01';
```

### Q: 水位站数量最多的河流

```sql
SELECT b.rvnm AS '河流名称', COUNT(b.stcd) AS '水位站数量'
FROM st_stbprp_b b
WHERE b.sttp = 'ZZ' AND b.rvnm IS NOT NULL AND b.rvnm != ''
GROUP BY b.rvnm ORDER BY COUNT(b.stcd) DESC LIMIT 1;
```

### Q: 查询建站最早和最晚的测站

```sql
SELECT stnm AS '测站名称', esstym AS '建站时间' FROM st_stbprp_b WHERE esstym = (SELECT MIN(esstym) FROM st_stbprp_b)
UNION ALL
SELECT stnm AS '测站名称', esstym AS '建站时间' FROM st_stbprp_b WHERE esstym = (SELECT MAX(esstym) FROM st_stbprp_b);
```

### Q: 瘦西湖水质监测的具体指标有哪些？哪些指标变化最显著？

```sql
SELECT r.stcd, b.stnm AS '测站名称', MAX(r.z) AS '当前水位(m)', rv.GRZ AS '排涝控制水位(m)',
       CASE WHEN MAX(r.z) > rv.GRZ THEN '超警戒' ELSE '正常' END AS '水位状态',
       CASE WHEN MAX(r.z) > rv.GRZ THEN '建议加大排水力度' ELSE '保持当前排水强度' END AS '调整建议'
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
JOIN st_rvfcch_b rv ON r.stcd = rv.STCD
WHERE b.addvcd LIKE '3210%' AND r.tm >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY r.stcd, b.stnm, rv.GRZ;
```

## 水库水位

### Q: 查询所有水库最新水位

```sql
SELECT b.stnm AS 水库名称, r.rz AS 库水位, r.inq AS 入库流量, r.otq AS 出库流量, r.tm AS 更新时间
FROM st_rsvr_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM st_rsvr_r GROUP BY stcd) latest
  ON r.stcd = latest.stcd AND r.tm = latest.maxTm
WHERE b.sttp = 'RR' ORDER BY r.rz DESC;
```

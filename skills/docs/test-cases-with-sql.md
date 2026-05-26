# 水利领域 Skill 测试用例集

> 基于实际数据库探查（2026-05-19）和 report_20250528.csv 测试用例分析
> 覆盖 6 个 Skill，每 Skill 10-20 题，按难度分为 L1(简单)/L2(中等)/L3(复杂)

---

## 1. water-situation（实时水位查询）

### L1 — 简单单表查询

**Q1:** 古运河有哪些水位测站？

```sql
SELECT stcd AS '测站编码', stnm AS '测站名称', sttp AS '测站类型'
FROM sl323.st_stbprp_b
WHERE rvnm LIKE '%古运河%' AND sttp = 'ZZ';
```

**Q2:** 查询宝应水位站的所属河流、水系、流域、测站类别。

```sql
SELECT stnm AS '测站名称', rvnm AS '河流', hnnm AS '水系', bsnm AS '流域', sttp AS '测站类别'
FROM sl323.st_stbprp_b
WHERE stnm = '宝应';
```

**Q3:** 查询测站总数。

```sql
SELECT COUNT(*) AS '测站总数'
FROM sl323.st_stbprp_b;
```

**Q4:** 查询水位站宝应最近30天水位数据。

```sql
SELECT r.tm AS '时间', r.z AS '水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%宝应%' AND b.sttp = 'ZZ'
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  AND r.z IS NOT NULL
ORDER BY r.tm;
```

### L2 — 多表关联、条件过滤

**Q5:** 查询古运河(河流名称)水位站的数量。

```sql
SELECT COUNT(*) AS '水位站数量'
FROM sl323.st_stbprp_b
WHERE rvnm LIKE '%古运河%' AND sttp = 'ZZ';
```

**Q6:** 查询建站最早和最晚的测站名称及其建站时间。

```sql
SELECT stnm AS '测站名称', esstym AS '建站时间'
FROM sl323.st_stbprp_b
WHERE esstym = (SELECT MIN(esstym) FROM sl323.st_stbprp_b)
UNION ALL
SELECT stnm AS '测站名称', esstym AS '建站时间'
FROM sl323.st_stbprp_b
WHERE esstym = (SELECT MAX(esstym) FROM sl323.st_stbprp_b);
```

**Q7:** 查询水位站数量最多、最少的河流。

```sql
SELECT b.rvnm AS '河流名称', COUNT(b.stcd) AS '水位站数量'
FROM sl323.st_stbprp_b b
WHERE b.sttp = 'ZZ' AND b.rvnm IS NOT NULL AND b.rvnm != ''
GROUP BY b.rvnm
HAVING COUNT(b.stcd) = (SELECT MIN(stcd_count) FROM (SELECT COUNT(stcd) AS stcd_count FROM sl323.st_stbprp_b WHERE sttp = 'ZZ' AND rvnm IS NOT NULL AND rvnm != '' GROUP BY rvnm) AS min_count)
   OR COUNT(b.stcd) = (SELECT MAX(stcd_count) FROM (SELECT COUNT(stcd) AS stcd_count FROM sl323.st_stbprp_b WHERE sttp = 'ZZ' AND rvnm IS NOT NULL AND rvnm != '' GROUP BY rvnm) AS max_count)
ORDER BY COUNT(b.stcd);
```

**Q8:** 查询古运河历史最高/低水位。

```sql
SELECT b.stnm AS '测站名称',
       MAX(r.z) AS '历史最高水位(m)',
       MIN(r.z) AS '历史最低水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%') AND r.z IS NOT NULL
GROUP BY b.stnm;
```

**Q9:** 查询里运河（河流）最近两个月的水位数据。

```sql
SELECT b.stnm AS '测站名称', r.z AS '水位(m)', r.tm AS '时间'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.rvnm = '里运河'
  AND r.tm >= DATE_SUB(NOW(), INTERVAL 2 MONTH)
  AND r.z IS NOT NULL
ORDER BY r.tm DESC;
```

**Q10:** 查询各水位站最新的水位值。

```sql
SELECT b.stnm AS '测站名称', r.z AS '最新水位(m)', r.tm AS '更新时间'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_river_r GROUP BY stcd) latest
  ON r.stcd = latest.stcd AND r.tm = latest.maxTm
WHERE b.sttp = 'ZZ'
ORDER BY r.z DESC;
```

### L3 — 复杂统计、跨年对比

**Q11:** 2024年古运河平均水位。

```sql
SELECT b.stnm AS '测站名称', AVG(r.z) AS '年平均水位'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%')
  AND r.tm BETWEEN '2024-01-01' AND '2024-12-31'
  AND r.z IS NOT NULL
GROUP BY b.stnm;
```

**Q12:** 古运河2024年2、3月份水位对比。

```sql
SELECT b.stnm AS '测站名称',
       DATE_FORMAT(r.tm, '%Y-%m') AS '月份',
       AVG(r.z) AS '月平均水位',
       MAX(r.z) AS '月最高水位',
       MIN(r.z) AS '月最低水位'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%')
  AND DATE_FORMAT(r.tm, '%Y-%m') IN ('2024-02', '2024-03')
  AND r.z IS NOT NULL
GROUP BY b.stnm, DATE_FORMAT(r.tm, '%Y-%m')
ORDER BY b.stnm, DATE_FORMAT(r.tm, '%Y-%m');
```

**Q13:** 请比较2023年和2024年古运河的平均水位。

```sql
SELECT YEAR(r.tm) AS '年份', AVG(r.z) AS '年平均水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%')
  AND YEAR(r.tm) IN (2023, 2024)
  AND r.z IS NOT NULL
GROUP BY YEAR(r.tm)
ORDER BY YEAR(r.tm);
```

**Q14:** 古运河2024年2月水位分布情况。

```sql
SELECT b.stnm AS '测站名称',
       AVG(r.z) AS '平均水位',
       MAX(r.z) AS '最高水位',
       MIN(r.z) AS '最低水位',
       MAX(r.z) - MIN(r.z) AS '水位变幅'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%')
  AND r.tm >= '2024-02-01' AND r.tm < '2024-03-01'
  AND r.z IS NOT NULL
GROUP BY b.stnm;
```

**Q15:** 查询水位站白马闸的实时水位是多少。

```sql
SELECT r.tm AS '时间', r.z AS '水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm = '白马闸' AND r.z IS NOT NULL
ORDER BY r.tm DESC
LIMIT 1;
```

**Q16:** 查询各类型测站的数量。

```sql
SELECT sttp AS '测站类型', COUNT(*) AS '数量'
FROM sl323.st_stbprp_b
GROUP BY sttp
ORDER BY COUNT(*) DESC;
```

**Q17:** 查询全部测站的名称（分页展示前20条）。

```sql
SELECT stcd AS '测站编码', stnm AS '测站名称', sttp AS '类型', rvnm AS '河流'
FROM sl323.st_stbprp_b
LIMIT 20;
```

**Q18:** 古运河水情（模糊查询，用户只输入"古运河"三个字）。

```sql
SELECT b.stnm AS '测站名称', r.z AS '水位(m)', r.q AS '流量(m³/s)', r.tm AS '更新时间'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%')
  AND r.tm = (SELECT MAX(r2.tm) FROM sl323.st_river_r r2 WHERE r2.stcd = r.stcd)
  AND r.z IS NOT NULL
ORDER BY r.tm DESC;
```

**Q19:** 查询2025年古运河水位站点的数量。

```sql
SELECT COUNT(DISTINCT r.stcd) AS '水位站点数量'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.sttp = 'ZZ' AND (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%')
  AND r.tm >= '2025-01-01' AND r.tm < '2026-01-01';
```

**Q20:** 扬州水利枢纽3月份平均水位。

```sql
SELECT b.stnm AS '测站名称', AVG(r.z) AS '3月平均水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%扬州水利枢纽%'
  AND r.tm >= '2025-03-01' AND r.tm < '2025-04-01'
  AND r.z IS NOT NULL
GROUP BY b.stnm;
```

**Q21:** 查询里运河2025年各测站的平均水位。

```sql
SELECT b.stnm AS '测站名称', AVG(r.z) AS '年平均水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.rvnm = '里运河' AND YEAR(r.tm) = 2025
  AND r.z IS NOT NULL
GROUP BY b.stnm
ORDER BY AVG(r.z) DESC;
```

**Q22:** 查询水位站宝应这个月的水位数据（同义词测试：本月 = 当月）。

```sql
SELECT r.tm AS '时间', r.z AS '水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%宝应%' AND b.sttp = 'ZZ'
  AND DATE_FORMAT(r.tm, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
  AND r.z IS NOT NULL
ORDER BY r.tm;
```

**Q23:** 查询水位站宝应本月内水位数据变化趋势。

```sql
SELECT DATE(r.tm) AS '日期', AVG(r.z) AS '日平均水位(m)', MAX(r.z) AS '日最高水位(m)', MIN(r.z) AS '日最低水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%宝应%' AND b.sttp = 'ZZ'
  AND DATE_FORMAT(r.tm, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
  AND r.z IS NOT NULL
GROUP BY DATE(r.tm)
ORDER BY DATE(r.tm);
```

**Q24:** 古运河8月的水位数据与扬州闸6月的水位数据对比，各自的平均水位、最高水位和最低水位分别是多少？

```sql
SELECT b.stnm AS '测站名称',
       CASE WHEN b.stnm LIKE '%古运河%' THEN '2024年8月' ELSE '2024年6月' END AS '时段',
       AVG(r.z) AS '平均水位(m)', MAX(r.z) AS '最高水位(m)', MIN(r.z) AS '最低水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE ((b.stnm LIKE '%古运河%' AND r.tm >= '2024-08-01' AND r.tm < '2024-09-01')
    OR (b.stnm LIKE '%扬州闸%' AND r.tm >= '2024-06-01' AND r.tm < '2024-07-01'))
  AND r.z IS NOT NULL
GROUP BY b.stnm,
         CASE WHEN b.stnm LIKE '%古运河%' THEN '2024年8月' ELSE '2024年6月' END
ORDER BY b.stnm;
```

**Q25:** 查询2024年古运河相关测站的年平均水位。

```sql
SELECT b.stnm AS '测站名称', AVG(r.z) AS '年平均水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%')
  AND r.tm BETWEEN '2024-01-01' AND '2024-12-31'
  AND r.z IS NOT NULL
GROUP BY b.stnm
ORDER BY AVG(r.z) DESC;
```

---

## 2. rainfall（降雨查询）

### L1 — 简单查询

**Q1:** 查询扬州城区今日降雨量。

```sql
SELECT DATE(p.tm) AS '日期', SUM(p.drp) AS '日降雨量(mm)'
FROM sl323.st_pptn_r p
WHERE p.stcd = '58245'
  AND DATE(p.tm) = CURDATE()
  AND p.drp IS NOT NULL
GROUP BY DATE(p.tm);
```

**Q2:** 查询2025年扬州城区降雨总量。

```sql
SELECT SUM(p.drp) AS '2025年累计降雨量(mm)'
FROM sl323.st_pptn_r p
WHERE p.stcd = '58245'
  AND p.tm BETWEEN '2025-01-01' AND '2025-12-31'
  AND p.drp IS NOT NULL;
```

**Q3:** 查询各雨量站的平均日降雨量。

```sql
SELECT b.stnm AS '雨量站名称', AVG(p.drp) AS '平均日降雨量(mm)'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP' AND p.drp IS NOT NULL
GROUP BY b.stnm;
```

### L2 — 多表、条件过滤、排序

**Q4:** 24年扬州城区降雨总量大概是多少？哪天降雨最大？

```sql
SELECT
  (SELECT SUM(drp) FROM sl323.st_pptn_r WHERE stcd = '58245' AND tm BETWEEN '2024-01-01' AND '2024-12-31' AND drp IS NOT NULL) AS '扬州城区2024年总降雨量',
  (SELECT DATE(tm) FROM sl323.st_pptn_r WHERE stcd = '58245' AND tm BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY DATE(tm) ORDER BY SUM(drp) DESC LIMIT 1) AS '最大降雨日期',
  (SELECT SUM(drp) FROM sl323.st_pptn_r WHERE stcd = '58245' AND tm BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY DATE(tm) ORDER BY SUM(drp) DESC LIMIT 1) AS '最大日降雨量';
```

**Q5:** 2024年扬州各区域累计降雨量最高的前三个区域。

```sql
SELECT p.addvcd AS '行政区划码', AVG(p.drp) AS '累计降水量(mm)'
FROM (
  SELECT b.addvcd, b.stcd, SUM(p.drp) AS drp
  FROM sl323.st_pptn_r p
  JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
  WHERE p.tm BETWEEN '2024-01-01' AND '2024-12-31'
    AND p.drp IS NOT NULL
    AND b.addvcd IS NOT NULL AND b.addvcd != ''
  GROUP BY b.addvcd, b.stcd
) p
GROUP BY p.addvcd
ORDER BY AVG(p.drp) DESC
LIMIT 3;
```

**Q6:** 查询最近三天各雨量站的累计降雨量。

```sql
SELECT b.stnm AS '雨量站名称', SUM(p.drp) AS '累计降雨量(mm)'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP'
  AND p.tm >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)
  AND p.drp IS NOT NULL
GROUP BY b.stnm
ORDER BY SUM(p.drp) DESC;
```

### L3 — 短临预测、复杂统计

**Q7:** 查询未来2小时短临扬州市区降雨预测。

```sql
SELECT f.ID AS '网格编号', i.adcd_name AS '区域',
       f.YMDH AS '预测时间', f.RN AS '预测降雨量(mm)'
FROM sl323.f_rnfl_h f
JOIN sl323.f_rnfl_info_r i ON f.ID = i.id
WHERE f.UNITNAME = '2'
  AND f.TYPE = '2'
  AND i.adcd_name = '扬州城区'
  AND f.FYMDH = (SELECT MAX(FYMDH) FROM sl323.f_rnfl_h WHERE UNITNAME = '2' AND TYPE = '2')
  AND f.YMDH >= NOW()
ORDER BY f.YMDH;
```

**Q8:** 查询2024年扬州城区哪天降雨量最大。

```sql
SELECT DATE(p.tm) AS '日期', SUM(p.drp) AS '总降水量(mm)'
FROM sl323.st_pptn_r p
WHERE p.stcd = '58245'
  AND p.tm BETWEEN '2024-01-01' AND '2024-12-31'
  AND p.drp IS NOT NULL
GROUP BY DATE(p.tm)
ORDER BY SUM(p.drp) DESC
LIMIT 1;
```

**Q9:** 扬州城区历史最大单日降雨量是多少？出现在哪一天？

```sql
SELECT DATE(p.tm) AS '日期', SUM(p.drp) AS '日降雨量(mm)'
FROM sl323.st_pptn_r p
WHERE p.stcd = '58245' AND p.drp IS NOT NULL
GROUP BY DATE(p.tm)
ORDER BY SUM(p.drp) DESC
LIMIT 1;
```

**Q10:** 查询最近三年各雨量站的年降雨量。

```sql
SELECT b.stnm AS '雨量站', YEAR(p.tm) AS '年份', SUM(p.drp) AS '年降雨量(mm)'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP'
  AND p.tm >= '2023-01-01' AND p.tm < '2026-01-01'
  AND p.drp IS NOT NULL
GROUP BY b.stnm, YEAR(p.tm)
ORDER BY b.stnm, YEAR(p.tm);
```

**Q11:** 查询各雨量站的2026年的累计降雨量（预期结果为空）。

```sql
SELECT b.stnm AS '雨量站', SUM(p.drp) AS '2026年累计降雨量(mm)'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP'
  AND p.tm >= '2026-01-01' AND p.tm < '2027-01-01'
  AND p.drp IS NOT NULL
GROUP BY b.stnm;
```

**Q12:** 查询2024年扬州城区累计降雨量最高的前三天。

```sql
SELECT DATE(p.tm) AS '日期', SUM(p.drp) AS '日降雨量(mm)'
FROM sl323.st_pptn_r p
WHERE p.stcd = '58245'
  AND p.tm BETWEEN '2024-01-01' AND '2024-12-31'
  AND p.drp IS NOT NULL
GROUP BY DATE(p.tm)
ORDER BY SUM(p.drp) DESC
LIMIT 3;
```

**Q13:** 查询2026年累计降雨量最多/最少的测站（预期结果为空，测试空结果处理）。

```sql
SELECT b.stnm AS '测站名称', SUM(p.drp) AS '累计降雨量(mm)'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP'
  AND p.tm >= '2026-01-01' AND p.tm < '2027-01-01'
  AND p.drp IS NOT NULL
GROUP BY b.stnm
ORDER BY SUM(p.drp) DESC
LIMIT 1;
```

**Q14:** 请帮我查询一下24年扬州城区降雨总量，按月统计。

```sql
SELECT DATE_FORMAT(p.tm, '%Y-%m') AS '月份', SUM(p.drp) AS '月累计降雨量(mm)'
FROM sl323.st_pptn_r p
WHERE p.stcd = '58245'
  AND p.tm BETWEEN '2024-01-01' AND '2024-12-31'
  AND p.drp IS NOT NULL
GROUP BY DATE_FORMAT(p.tm, '%Y-%m')
ORDER BY DATE_FORMAT(p.tm, '%Y-%m');
```

**Q15:** 对比2023年和2024年扬州城区各月降雨量。

```sql
SELECT DATE_FORMAT(p.tm, '%m') AS '月份',
       SUM(CASE WHEN YEAR(p.tm) = 2023 THEN p.drp ELSE 0 END) AS '2023年(mm)',
       SUM(CASE WHEN YEAR(p.tm) = 2024 THEN p.drp ELSE 0 END) AS '2024年(mm)'
FROM sl323.st_pptn_r p
WHERE p.stcd = '58245'
  AND p.tm BETWEEN '2023-01-01' AND '2024-12-31'
  AND p.drp IS NOT NULL
GROUP BY DATE_FORMAT(p.tm, '%m')
ORDER BY DATE_FORMAT(p.tm, '%m');
```

**Q16:** 查询今天有没有下雨？扬州城区当前降雨情况。

```sql
SELECT p.tm AS '时间', p.drp AS '时段降雨量(mm)'
FROM sl323.st_pptn_r p
WHERE p.stcd = '58245'
  AND DATE(p.tm) = CURDATE()
  AND p.drp IS NOT NULL AND p.drp > 0
ORDER BY p.tm DESC;
```

**Q17:** 查询最近一周扬州市各雨量站的累计降雨量排名。

```sql
SELECT b.stnm AS '雨量站', SUM(p.drp) AS '累计降雨量(mm)'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP'
  AND p.tm >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
  AND p.drp IS NOT NULL
GROUP BY b.stnm
ORDER BY SUM(p.drp) DESC;
```

**Q18:** 查询扬州城区2024年降雨日数（有雨的天数）。

```sql
SELECT COUNT(DISTINCT DATE(tm)) AS '降雨天数'
FROM sl323.st_pptn_r
WHERE stcd = '58245'
  AND tm BETWEEN '2024-01-01' AND '2024-12-31'
  AND drp IS NOT NULL AND drp > 0;
```

---

## 3. water-quality（水质查询）

### L1 — 简单查询

**Q1:** 瘦西湖水质当前如何。

```sql
SELECT b.stnm AS '测站名称', d.spt AS '采样时间',
       d.dox AS '溶解氧(mg/L)', d.codmn AS 'CODMn(mg/L)',
       d.nh3n AS '氨氮(mg/L)', d.tp AS '总磷(mg/L)',
       d.ph AS 'pH', d.wtmp AS '水温(℃)'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%瘦西湖%' AND b.sttp = 'WQ'
  AND d.spt = (SELECT MAX(d2.spt) FROM sl325.wq_pcp_d d2 WHERE d2.stcd = d.stcd);
```

**Q2:** 查询京杭运河水质站的最新水质指标。

```sql
SELECT b.stnm AS '测站名称', d.spt AS '采样时间',
       d.dox AS 'DO(mg/L)', d.codmn AS 'CODMn(mg/L)',
       d.nh3n AS 'NH3N(mg/L)', d.tp AS 'TP(mg/L)', d.ph AS 'pH'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%京杭运河%' AND b.sttp = 'WQ'
  AND d.spt = (SELECT MAX(d2.spt) FROM sl325.wq_pcp_d d2 WHERE d2.stcd = d.stcd);
```

### L2 — 趋势分析、评级

**Q3:** 帮我分析一下最近一个月瘦西湖水质变化趋势。

```sql
SELECT DATE(d.spt) AS '日期',
       AVG(d.dox) AS '平均溶解氧(mg/L)',
       AVG(d.codmn) AS '平均CODMn(mg/L)',
       AVG(d.nh3n) AS '平均氨氮(mg/L)',
       AVG(d.tp) AS '平均总磷(mg/L)',
       AVG(d.ph) AS '平均pH',
       AVG(d.wtmp) AS '平均水温(℃)'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%瘦西湖%' AND b.sttp = 'WQ'
  AND d.spt >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
  AND d.spt <= NOW()
GROUP BY DATE(d.spt)
ORDER BY DATE(d.spt);
```

**Q4:** 查询京杭运河水质站当前水质等级（单因子评价法）。

```sql
SELECT b.stnm AS '测站',
       d.codmn AS 'CODMn', d.dox AS 'DO', d.nh3n AS 'NH3N', d.tp AS 'TP',
       CASE
         WHEN d.codmn <= 2 THEN 'Ⅰ类' WHEN d.codmn <= 4 THEN 'Ⅱ类'
         WHEN d.codmn <= 6 THEN 'Ⅲ类' WHEN d.codmn <= 10 THEN 'Ⅳ类'
         WHEN d.codmn <= 15 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
       END AS 'CODMn评级',
       CASE
         WHEN d.dox >= 7.5 THEN 'Ⅰ类' WHEN d.dox >= 6 THEN 'Ⅱ类'
         WHEN d.dox >= 5 THEN 'Ⅲ类' WHEN d.dox >= 3 THEN 'Ⅳ类'
         WHEN d.dox >= 2 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
       END AS 'DO评级',
       CASE
         WHEN d.nh3n <= 0.15 THEN 'Ⅰ类' WHEN d.nh3n <= 0.5 THEN 'Ⅱ类'
         WHEN d.nh3n <= 1 THEN 'Ⅲ类' WHEN d.nh3n <= 1.5 THEN 'Ⅳ类'
         WHEN d.nh3n <= 2 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
       END AS 'NH3N评级',
       CASE
         WHEN d.tp <= 0.02 THEN 'Ⅰ类' WHEN d.tp <= 0.1 THEN 'Ⅱ类'
         WHEN d.tp <= 0.2 THEN 'Ⅲ类' WHEN d.tp <= 0.3 THEN 'Ⅳ类'
         WHEN d.tp <= 0.4 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
       END AS 'TP评级'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%京杭运河%' AND b.sttp = 'WQ'
  AND d.spt = (SELECT MAX(d2.spt) FROM sl325.wq_pcp_d d2 WHERE d2.stcd = d.stcd);
```

**Q5:** 查询所有水质站最新一条数据中，哪些指标劣于Ⅳ类。

```sql
SELECT b.stnm AS '测站名称', d.spt AS '采样时间',
       d.codmn, d.dox, d.nh3n, d.tp,
       CASE WHEN d.codmn > 10 THEN '超标' END AS 'CODMn状态',
       CASE WHEN d.dox < 3 THEN '超标' END AS 'DO状态',
       CASE WHEN d.nh3n > 1.5 THEN '超标' END AS 'NH3N状态',
       CASE WHEN d.tp > 0.3 THEN '超标' END AS 'TP状态'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.sttp = 'WQ'
  AND d.spt = (SELECT MAX(d2.spt) FROM sl325.wq_pcp_d d2 WHERE d2.stcd = d.stcd)
  AND (d.codmn > 10 OR d.dox < 3 OR d.nh3n > 1.5 OR d.tp > 0.3);
```

### L3 — 水质预测

**Q6:** 预测一下未来24小时瘦西湖水质指标值及评级。

```sql
SELECT stnm AS '测站', tm AS '预报时间',
       codmn AS 'CODMn(mg/L)', dox AS 'DO(mg/L)',
       nh3n AS 'NH3N(mg/L)', tp AS 'TP(mg/L)',
       CASE
         WHEN codmn <= 2 THEN 'Ⅰ类' WHEN codmn <= 4 THEN 'Ⅱ类'
         WHEN codmn <= 6 THEN 'Ⅲ类' WHEN codmn <= 10 THEN 'Ⅳ类'
         WHEN codmn <= 15 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
       END AS 'CODMn评级',
       CASE
         WHEN dox >= 7.5 THEN 'Ⅰ类' WHEN dox >= 6 THEN 'Ⅱ类'
         WHEN dox >= 5 THEN 'Ⅲ类' WHEN dox >= 3 THEN 'Ⅳ类'
         WHEN dox >= 2 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
       END AS 'DO评级',
       CASE
         WHEN nh3n <= 0.15 THEN 'Ⅰ类' WHEN nh3n <= 0.5 THEN 'Ⅱ类'
         WHEN nh3n <= 1 THEN 'Ⅲ类' WHEN nh3n <= 1.5 THEN 'Ⅳ类'
         WHEN nh3n <= 2 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
       END AS 'NH3N评级',
       CASE
         WHEN tp <= 0.02 THEN 'Ⅰ类' WHEN tp <= 0.1 THEN 'Ⅱ类'
         WHEN tp <= 0.2 THEN 'Ⅲ类' WHEN tp <= 0.3 THEN 'Ⅳ类'
         WHEN tp <= 0.4 THEN 'Ⅴ类' ELSE '劣Ⅴ类'
       END AS 'TP评级'
FROM (
  SELECT tm, b.stnm,
    MAX(CASE WHEN r.type = 104 THEN (SELECT value FROM slztk.wq_cod_pz WHERE min <= r.vals AND max > r.vals) END) AS codmn,
    MAX(CASE WHEN r.type = 103 THEN r.vals END) AS dox,
    MAX(CASE WHEN r.type = 128 THEN r.vals END) AS nh3n,
    MAX(CASE WHEN r.type = 105 THEN r.vals END) AS tp
  FROM slztk.st_mx_preset_r_shj_auto r
  JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
  WHERE b.sttp = 'WQ' AND b.stnm LIKE '%瘦西湖%'
    AND r.type IN (104, 103, 128, 105)
    AND r.tm BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
    AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_shj_auto WHERE state = '1' ORDER BY tm DESC LIMIT 1)
  GROUP BY tm, b.stnm
) sub
ORDER BY tm;
```

**Q7:** 瘦西湖水质监测的具体指标有哪些？最近一个月哪些指标变化最显著？

```sql
SELECT '溶解氧' AS '指标', MAX(dox) - MIN(dox) AS '变化幅度'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%瘦西湖%' AND b.sttp = 'WQ'
  AND d.spt >= DATE_SUB(NOW(), INTERVAL 1 MONTH) AND d.dox IS NOT NULL
UNION ALL
SELECT 'CODMn', MAX(codmn) - MIN(codmn)
FROM sl325.wq_pcp_d d JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%瘦西湖%' AND b.sttp = 'WQ'
  AND d.spt >= DATE_SUB(NOW(), INTERVAL 1 MONTH) AND d.codmn IS NOT NULL
UNION ALL
SELECT '氨氮', MAX(nh3n) - MIN(nh3n)
FROM sl325.wq_pcp_d d JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%瘦西湖%' AND b.sttp = 'WQ'
  AND d.spt >= DATE_SUB(NOW(), INTERVAL 1 MONTH) AND d.nh3n IS NOT NULL
UNION ALL
SELECT '总磷', MAX(tp) - MIN(tp)
FROM sl325.wq_pcp_d d JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%瘦西湖%' AND b.sttp = 'WQ'
  AND d.spt >= DATE_SUB(NOW(), INTERVAL 1 MONTH) AND d.tp IS NOT NULL
ORDER BY '变化幅度' DESC;
```

**Q8:** 查询一段时间内所有水质站的水质变化趋势。

```sql
SELECT DATE(d.spt) AS '日期', b.stnm AS '测站',
       AVG(d.dox) AS '平均DO(mg/L)', AVG(d.codmn) AS '平均CODMn(mg/L)',
       AVG(d.nh3n) AS '平均NH3N(mg/L)', AVG(d.tp) AS '平均TP(mg/L)',
       AVG(d.ph) AS '平均pH', AVG(d.wtmp) AS '平均水温(℃)'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.sttp = 'WQ'
  AND d.spt >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY DATE(d.spt), b.stnm
ORDER BY DATE(d.spt), b.stnm;
```

**Q9:** 查询所有水质站的最新数据，包含测站名称和所有指标。

```sql
SELECT b.stnm AS '测站名称', d.spt AS '采样时间',
       d.dox AS 'DO(mg/L)', d.codmn AS 'CODMn(mg/L)',
       d.nh3n AS 'NH3N(mg/L)', d.tp AS 'TP(mg/L)',
       d.ph AS 'pH', d.wtmp AS '水温(℃)',
       d.turb AS '浊度', d.cond AS '电导率(uS/cm)'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.sttp = 'WQ'
  AND d.spt = (SELECT MAX(d2.spt) FROM sl325.wq_pcp_d d2 WHERE d2.stcd = d.stcd)
ORDER BY b.stnm;
```

**Q10:** 查询京杭运河最近一周每天的CODMn变化。

```sql
SELECT DATE(d.spt) AS '日期', AVG(d.codmn) AS '平均CODMn(mg/L)'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%京杭运河%' AND b.sttp = 'WQ'
  AND d.spt >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
  AND d.codmn IS NOT NULL
GROUP BY DATE(d.spt)
ORDER BY DATE(d.spt);
```

**Q11:** 查询宝带河水质站的最新水质数据及综合评级。

```sql
SELECT b.stnm AS '测站', d.spt AS '采样时间',
       d.codmn AS 'CODMn', d.dox AS 'DO', d.nh3n AS 'NH3N', d.tp AS 'TP',
       CASE
         WHEN d.codmn > 15 OR d.dox < 2 OR d.nh3n > 2 OR d.tp > 0.4 THEN '劣Ⅴ类'
         WHEN d.codmn > 10 OR d.dox < 3 OR d.nh3n > 1.5 OR d.tp > 0.3 THEN 'Ⅴ类'
         WHEN d.codmn > 6 OR d.dox < 5 OR d.nh3n > 1 OR d.tp > 0.2 THEN 'Ⅳ类'
         WHEN d.codmn > 4 OR d.dox < 6 OR d.nh3n > 0.5 OR d.tp > 0.1 THEN 'Ⅲ类'
         WHEN d.codmn > 2 OR d.dox < 7.5 OR d.nh3n > 0.15 OR d.tp > 0.02 THEN 'Ⅱ类'
         ELSE 'Ⅰ类'
       END AS '综合水质等级(单因子)'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%宝带河%' AND b.sttp = 'WQ'
  AND d.spt = (SELECT MAX(d2.spt) FROM sl325.wq_pcp_d d2 WHERE d2.stcd = d.stcd);
```

**Q12:** 帮我分析一下最近一个月仪扬河上游水质变化趋势。

```sql
SELECT DATE(d.spt) AS '日期',
       AVG(d.dox) AS '平均DO(mg/L)', AVG(d.codmn) AS '平均CODMn(mg/L)',
       AVG(d.nh3n) AS '平均NH3N(mg/L)', AVG(d.tp) AS '平均TP(mg/L)'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.stnm LIKE '%仪扬河%' AND b.sttp = 'WQ'
  AND d.spt >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
GROUP BY DATE(d.spt)
ORDER BY DATE(d.spt);
```

**Q13:** 查询有哪些水质站？分别属于哪条河流？

```sql
SELECT b.stnm AS '水质站名称', b.rvnm AS '河流', b.stcd AS '测站编码'
FROM sl323.st_stbprp_b
WHERE sttp = 'WQ'
ORDER BY b.rvnm, b.stnm;
```

---

## 4. water-forecast（水位预测）

### L1 — 简单预测查询

**Q1:** 查询未来24小时扬州市重点河道水位预测。

```sql
SELECT taskid, r.stcd AS '测站编码', REPLACE(b.stnm, '计算水位', '') AS '测站名称',
       tm AS '预报时间', vals AS '预报值'
FROM slztk.st_mx_preset_cal_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）',
                  '七里河水位站（东花园路）', '赵家支沟水文站（赵家河路）', '瘦西湖水位站')
  AND tm >= NOW() AND tm <= DATE_ADD(NOW(), INTERVAL 24 HOUR)
  AND type = '1'
  AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r WHERE stuts = '1' ORDER BY tm DESC LIMIT 1)
ORDER BY tm;
```

**Q2:** 查询最新预测任务的状态。

```sql
SELECT taskid AS '任务ID', tm AS '调度开始时间',
       CASE WHEN stuts = '0' THEN '未完成' WHEN stuts = '1' THEN '已完成' END AS '状态',
       CASE WHEN type = '1' THEN '滚动预报' WHEN type = '2' THEN '模型计算' END AS '任务类型'
FROM slztk.st_mx_taskid_r
ORDER BY tm DESC
LIMIT 10;
```

### L2 — 指定站点预测

**Q3:** 预测未来24小时古运河水位站的水位变化趋势。

```sql
SELECT r.tm AS '预报时间', r.vals AS '预报水位(m)'
FROM slztk.st_mx_preset_cal_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%古运河%'
  AND r.type = '1'
  AND r.tm BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
  AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r WHERE stuts = '1' ORDER BY tm DESC LIMIT 1)
ORDER BY r.tm;
```

**Q4:** 查询未来24小时所有站点的预测水位，按站分组显示最高/最低预测值。

```sql
SELECT b.stnm AS '测站名称',
       MIN(r.vals) AS '最低预测水位(m)',
       MAX(r.vals) AS '最高预测水位(m)',
       MIN(r.tm) AS '预测起始',
       MAX(r.tm) AS '预测终止'
FROM slztk.st_mx_preset_cal_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE r.type = '1'
  AND r.tm BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
  AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r WHERE stuts = '1' ORDER BY tm DESC LIMIT 1)
GROUP BY b.stnm
ORDER BY MAX(r.vals) DESC;
```

**Q5:** 查询最新的模型计算任务列表（已完成的）。

```sql
SELECT taskid AS '任务ID', tm AS '调度时间', task_name AS '任务名称',
       calTm AS '计算完成时间'
FROM slztk.st_mx_taskid_r
WHERE stuts = '1' AND type = '1'
ORDER BY tm DESC
LIMIT 20;
```

### L3 — 对比分析

**Q6:** 对比当前水位与未来24小时预测水位的差异。

```sql
SELECT b.stnm AS '测站名称',
       latest.z AS '当前水位(m)',
       pred.vals AS '预测水位(m)',
       pred.vals - latest.z AS '水位变化(m)',
       pred.tm AS '预测时间'
FROM slztk.st_mx_preset_cal_r pred
JOIN sl323.st_stbprp_b b ON pred.stcd = b.stcd
JOIN (
  SELECT r.stcd, r.z
  FROM sl323.st_river_r r
  JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_river_r GROUP BY stcd) l
    ON r.stcd = l.stcd AND r.tm = l.maxTm
) latest ON pred.stcd = latest.stcd
WHERE pred.type = '1'
  AND pred.tm BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
  AND pred.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r WHERE stuts = '1' ORDER BY tm DESC LIMIT 1)
ORDER BY ABS(pred.vals - latest.z) DESC;
```

**Q7:** 查询河道断面数据（某任务下的所有断面水位）。

```sql
SELECT dm.name AS '断面名称', dm.z AS '水位(m)', dm.Qin AS '入流(m³/s)', dm.Qout AS '出流(m³/s)', dm.tm AS '时间'
FROM slztk.st_mx_rv_dm_r dm
WHERE dm.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r WHERE stuts = '1' ORDER BY tm DESC LIMIT 1)
ORDER BY dm.tm DESC, dm.name
LIMIT 50;
```

**Q8:** 查询最新已完成任务的预测起止时间。

```sql
SELECT taskid AS '任务ID', tm AS '调度开始时间', endTm AS '调度结束时间',
       calTm AS '计算完成时间', task_name AS '任务名称'
FROM slztk.st_mx_taskid_r
WHERE stuts = '1'
ORDER BY tm DESC
LIMIT 1;
```

**Q9:** 查询未来24小时所有站点的预测流量（type='2'）。

```sql
SELECT b.stnm AS '测站名称', r.tm AS '预报时间', r.vals AS '预报流量(m³/s)'
FROM slztk.st_mx_preset_cal_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE r.type = '2'
  AND r.tm BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
  AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r WHERE stuts = '1' ORDER BY tm DESC LIMIT 1)
ORDER BY r.tm;
```

**Q10:** 查询历史上有多少次预测任务已完成。

```sql
SELECT
  COUNT(*) AS '总任务数',
  SUM(CASE WHEN stuts = '1' THEN 1 ELSE 0 END) AS '已完成',
  SUM(CASE WHEN stuts = '0' THEN 1 ELSE 0 END) AS '未完成'
FROM slztk.st_mx_taskid_r;
```

**Q11:** 预测瘦西湖未来24小时水位变化。

```sql
SELECT r.tm AS '预报时间', r.vals AS '预报水位(m)'
FROM slztk.st_mx_preset_cal_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%瘦西湖%'
  AND r.type = '1'
  AND r.tm BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
  AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r WHERE stuts = '1' ORDER BY tm DESC LIMIT 1)
ORDER BY r.tm;
```

**Q12:** 查询最新任务中预测水位最高和最低的站点。

```sql
SELECT b.stnm AS '测站名称', MAX(r.vals) AS '最高预测水位(m)', MIN(r.vals) AS '最低预测水位(m)'
FROM slztk.st_mx_preset_cal_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE r.type = '1'
  AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r WHERE stuts = '1' ORDER BY tm DESC LIMIT 1)
GROUP BY b.stnm
ORDER BY MAX(r.vals) DESC
LIMIT 5;
```

**Q13:** 查询今天有哪些预测任务，分别是什么状态？

```sql
SELECT taskid AS '任务ID', tm AS '调度时间',
       CASE WHEN stuts = '0' THEN '计算中' WHEN stuts = '1' THEN '已完成' END AS '状态',
       CASE WHEN type = '1' THEN '滚动预报' WHEN type = '2' THEN '模型计算' END AS '类型'
FROM slztk.st_mx_taskid_r
WHERE DATE(tm) = CURDATE()
ORDER BY tm DESC;
```

---

## 5. gate-pump-operation（闸泵工况）

### L1 — 简单查询

**Q1:** 查询所有闸站的最新启闭状态。

```sql
SELECT b.stnm AS '闸站名称', g.gtname AS '闸门名称', g.tm AS '更新时间',
       g.gtophgt AS '闸门开度(m)', g.gto AS '过闸流量(m³/s)',
       CASE WHEN g.gtophgt > 0 THEN '已开启' ELSE '已关闭' END AS '状态'
FROM sl323.st_gate_r g
JOIN sl323.st_stbprp_b b ON g.stcd = b.stcd
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_gate_r GROUP BY stcd) latest
  ON g.stcd = latest.stcd AND g.tm = latest.maxTm
WHERE b.sttp = 'DD'
ORDER BY g.tm DESC;
```

**Q2:** 查询当前开启状态的泵站最新水情数据。

```sql
SELECT p.tm AS '时间', b.stnm AS '泵站名称', p.pumpname AS '泵名称',
       p.ppupz AS '站上水位(m)', p.ppdwz AS '站下水位(m)',
       p.omcn AS '开机台数', p.pmpq AS '抽水流量(m³/s)',
       CASE WHEN p.pdchcd = '1' THEN '引水' WHEN p.pdchcd = '2' THEN '排水' ELSE '未知' END AS '引排特征'
FROM sl323.st_pump_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'DP'
  AND p.tm = (SELECT MAX(p2.tm) FROM sl323.st_pump_r p2 WHERE p2.stcd = p.stcd)
  AND p.omcn > 0
ORDER BY p.tm DESC;
```

### L2 — 多表综合查询

**Q3:** 查询念四闸站最新的上下游水位和过闸流量。

```sql
SELECT b.stnm AS '闸站名称', w.tm AS '更新时间',
       w.upz AS '闸上水位(m)', w.dwz AS '闸下水位(m)',
       w.tgtq AS '过闸流量(m³/s)',
       w.upz - w.dwz AS '水位差(m)'
FROM sl323.st_was_r w
JOIN sl323.st_stbprp_b b ON w.stcd = b.stcd
WHERE b.stnm = '念四闸站'
ORDER BY w.tm DESC
LIMIT 1;
```

**Q4:** 查询泵站综合运行状态汇总。

```sql
SELECT b.stnm AS '泵站名称',
       SUM(CASE WHEN p.omcn > 0 THEN 1 ELSE 0 END) AS '运行泵数',
       MAX(p.omcn) AS '开机台数',
       SUM(p.pmpq) AS '总抽水流量(m³/s)',
       CASE WHEN MAX(p.pdchcd) = '1' THEN '引水'
            WHEN MAX(p.pdchcd) = '2' THEN '排水'
            ELSE '未知' END AS '引排特征'
FROM sl323.st_pump_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'DP'
  AND p.tm = (SELECT MAX(p2.tm) FROM sl323.st_pump_r p2 WHERE p2.stcd = p.stcd)
GROUP BY b.stnm;
```

**Q5:** 查询润扬河闸各闸门最新开度。

```sql
SELECT b.stnm AS '闸站', g.gtname AS '闸门名称', g.gtophgt AS '开度(m)',
       g.gto AS '过闸流量(m³/s)', g.tm AS '时间',
       CASE WHEN g.gtophgt > 0 THEN '开启' ELSE '关闭' END AS '状态'
FROM sl323.st_gate_r g
JOIN sl323.st_stbprp_b b ON g.stcd = b.stcd
WHERE b.stnm = '润扬河闸'
  AND g.tm = (SELECT MAX(g2.tm) FROM sl323.st_gate_r g2 WHERE g2.stcd = g.stcd)
ORDER BY g.gtname;
```

### L3 — 复杂工况分析

**Q6:** 查询当前所有正在排水的泵站及其抽水流量排名。

```sql
SELECT b.stnm AS '泵站名称', p.pmpq AS '抽水流量(m³/s)',
       p.ppupz AS '站上水位(m)', p.ppdwz AS '站下水位(m)',
       p.ppupz - p.ppdwz AS '水头差(m)'
FROM sl323.st_pump_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'DP'
  AND p.pdchcd = '2'
  AND p.omcn > 0
  AND p.tm = (SELECT MAX(p2.tm) FROM sl323.st_pump_r p2 WHERE p2.stcd = p.stcd)
ORDER BY p.pmpq DESC;
```

**Q7:** 查询当前所有堰闸的水位差排名（上下游水位差最大的前10）。

```sql
SELECT b.stnm AS '闸站名称', w.upz AS '闸上水位(m)', w.dwz AS '闸下水位(m)',
       w.upz - w.dwz AS '水位差(m)', w.tgtq AS '过闸流量(m³/s)'
FROM sl323.st_was_r w
JOIN sl323.st_stbprp_b b ON w.stcd = b.stcd
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_was_r GROUP BY stcd) latest
  ON w.stcd = latest.stcd AND w.tm = latest.maxTm
WHERE w.upz IS NOT NULL AND w.dwz IS NOT NULL
ORDER BY w.upz - w.dwz DESC
LIMIT 10;
```

**Q8:** 查询军桥站各泵的最新工情数据（电压、电流、功率）。

```sql
SELECT b.stnm AS '泵站', pa.pumpname AS '设备名称',
       CASE WHEN pa.switch = 1 THEN '开' WHEN pa.switch = 0 THEN '关' ELSE '未知' END AS '状态',
       pa.ua AS 'UA(V)', pa.ub AS 'UB(V)', pa.uc AS 'UC(V)',
       pa.ia AS 'IA(A)', pa.ib AS 'IB(A)', pa.ic AS 'IC(A)',
       pa.ps AS '总有功功率(KW)', pa.fr AS '频率(Hz)', pa.tm AS '时间'
FROM sl323.st_pump_pa pa
JOIN sl323.st_stbprp_b b ON pa.stcd = b.stcd
WHERE b.stnm LIKE '%军桥%'
  AND pa.tm = (SELECT MAX(pa2.tm) FROM sl323.st_pump_pa pa2 WHERE pa2.stcd = pa.stcd)
ORDER BY pa.pumpname;
```

**Q9:** 查询当前所有正在引水的泵站及其引水量。

```sql
SELECT b.stnm AS '泵站名称', p.pmpq AS '引水流量(m³/s)',
       p.ppupz AS '站上水位(m)', p.ppdwz AS '站下水位(m)', p.omcn AS '开机台数'
FROM sl323.st_pump_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'DP' AND p.pdchcd = '1'
  AND p.tm = (SELECT MAX(p2.tm) FROM sl323.st_pump_r p2 WHERE p2.stcd = p.stcd)
ORDER BY p.pmpq DESC;
```

**Q10:** 查询戴庄排涝站闸门的开度历史记录（最近10条）。

```sql
SELECT b.stnm AS '闸站', g.gtname AS '闸门', g.gtophgt AS '开度(m)', g.tm AS '时间'
FROM sl323.st_gate_r g
JOIN sl323.st_stbprp_b b ON g.stcd = b.stcd
WHERE b.stnm LIKE '%戴庄%'
ORDER BY g.tm DESC
LIMIT 10;
```

**Q11:** 查询新城河闸上下游水位及过闸流量（堰闸水情）。

```sql
SELECT b.stnm AS '闸站', w.upz AS '闸上水位(m)', w.dwz AS '闸下水位(m)',
       w.tgtq AS '过闸流量(m³/s)', w.tm AS '时间'
FROM sl323.st_was_r w
JOIN sl323.st_stbprp_b b ON w.stcd = b.stcd
WHERE b.stnm LIKE '%新城河%'
ORDER BY w.tm DESC
LIMIT 1;
```

**Q12:** 查询所有闸门的开启孔数统计。

```sql
SELECT b.stnm AS '闸站', g.gtname AS '闸门', g.gtopnum AS '开启孔数', g.gtophgt AS '开度(m)'
FROM sl323.st_gate_r g
JOIN sl323.st_stbprp_b b ON g.stcd = b.stcd
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_gate_r GROUP BY stcd) latest
  ON g.stcd = latest.stcd AND g.tm = latest.maxTm
WHERE g.gtopnum IS NOT NULL AND g.gtopnum > 0
ORDER BY g.gtopnum DESC;
```

**Q13:** 统计当前有多少闸门处于开启状态、多少处于关闭状态。

```sql
SELECT
  SUM(CASE WHEN g.gtophgt > 0 THEN 1 ELSE 0 END) AS '开启闸门数',
  SUM(CASE WHEN g.gtophgt = 0 OR g.gtophgt IS NULL THEN 1 ELSE 0 END) AS '关闭闸门数'
FROM sl323.st_gate_r g
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_gate_r GROUP BY stcd) latest
  ON g.stcd = latest.stcd AND g.tm = latest.maxTm;
```

**Q14:** 查询有哪些闸站和泵站？分别属于哪个管理区域？

```sql
SELECT b.stnm AS '名称', b.sttp AS '类型',
       CASE WHEN b.sttp = 'DD' THEN '闸站' WHEN b.sttp = 'DP' THEN '泵站' END AS '类型说明',
       b.addvcd AS '行政区划'
FROM sl323.st_stbprp_b b
WHERE b.sttp IN ('DD', 'DP')
ORDER BY b.sttp, b.stnm;
```

**Q15:** 查询扬州水利枢纽泵站当前的运行状态。

```sql
SELECT b.stnm AS '泵站', p.pumpname AS '泵名',
       p.omcn AS '开机台数', p.pmpq AS '抽水流量(m³/s)',
       p.ppupz AS '站上水位(m)', p.ppdwz AS '站下水位(m)',
       p.pdchcd AS '引排特征码', p.tm AS '时间'
FROM sl323.st_pump_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.stnm LIKE '%扬州水利枢纽%'
  AND p.tm = (SELECT MAX(p2.tm) FROM sl323.st_pump_r p2 WHERE p2.stcd = p.stcd)
ORDER BY p.pumpname;
```

---

## 6. water-warning（水利预警）

### L1 — 简单预警

**Q1:** 查询当前超警戒水位的站点。

```sql
SELECT b.stnm AS '测站名称', r.z AS '当前水位(m)', rv.WRZ AS '警戒水位(m)',
       rv.GRZ AS '保证水位(m)', r.tm AS '更新时间',
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

**Q2:** 查询防洪预警汇总（多少站正常、超警戒、超保证）。

```sql
SELECT
  COUNT(*) AS '监测站点总数',
  SUM(CASE WHEN r.z > rv.WRZ THEN 1 ELSE 0 END) AS '超警戒站点数',
  SUM(CASE WHEN r.z > rv.GRZ THEN 1 ELSE 0 END) AS '超保证站点数',
  SUM(CASE WHEN r.z <= rv.WRZ THEN 1 ELSE 0 END) AS '正常站点数'
FROM sl323.st_river_r r
JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_river_r GROUP BY stcd) latest
  ON r.stcd = latest.stcd AND r.tm = latest.maxTm
WHERE rv.WRZ IS NOT NULL;
```

### L2 — 重点河道预警

**Q3:** 扬州市重点河道水位实时情况（含超警戒判断）。

```sql
SELECT b.stnm AS '测站名称', r.z AS '实时水位(m)', r.tm AS '更新时间',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN r.z > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
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

**Q4:** 查询水质低于Ⅳ类的站点。

```sql
SELECT b.stnm AS '测站名称', d.spt AS '采样时间',
       d.codmn AS 'CODMn', d.dox AS 'DO', d.nh3n AS 'NH3N', d.tp AS 'TP',
       CASE
         WHEN d.codmn > 10 OR d.dox < 3 OR d.nh3n > 1.5 OR d.tp > 0.3 THEN '劣于Ⅳ类'
         ELSE '正常'
       END AS '预警状态'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.sttp = 'WQ'
  AND d.spt = (SELECT MAX(d2.spt) FROM sl325.wq_pcp_d d2 WHERE d2.stcd = d.stcd)
  AND (d.codmn > 10 OR d.dox < 3 OR d.nh3n > 1.5 OR d.tp > 0.3);
```

**Q5:** 扬州市重点河道指定测站当前水位如何。

```sql
SELECT b.stnm AS '测站名称', r.z AS '当前水位(m)', r.tm AS '更新时间',
       rv.WRZ AS '警戒水位(m)', rv.GRZ AS '保证水位(m)',
       CASE
         WHEN r.z > rv.GRZ THEN '超保证'
         WHEN r.z > rv.WRZ THEN '超警戒'
         ELSE '正常'
       END AS '预警状态'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_river_r GROUP BY stcd) latest
  ON r.stcd = latest.stcd AND r.tm = latest.maxTm
WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）',
                  '七里河水位站（东花园路）', '赵家支沟水文站（赵家河路）', '瘦西湖水位站');
```

### L3 — 历史对比预警

**Q6:** 24年8月20号左右，扬州古运河、新城河、瘦西湖最高水位及是否超标。

```sql
SELECT b.stnm AS '测站名称', sub.max_z AS '最高水位(m)', sub.max_time AS '出现时间',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN sub.max_z > rv.WRZ THEN '是' ELSE '否' END AS '是否超警戒'
FROM sl323.st_stbprp_b b
INNER JOIN (
  SELECT stcd, MAX(z) AS max_z, MAX(tm) AS max_time
  FROM sl323.st_river_r
  WHERE tm BETWEEN '2024-08-17' AND '2024-08-23'
  GROUP BY stcd
) AS sub ON b.stcd = sub.stcd
INNER JOIN sl323.st_rvfcch_b rv ON b.stcd = rv.STCD
WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）', '瘦西湖水位站')
ORDER BY b.stnm;
```

**Q7:** 查询所有站点的预警水位配置（有警戒水位的站）。

```sql
SELECT rv.STCD AS '测站编码', b.stnm AS '测站名称',
       rv.WRZ AS '警戒水位(m)', rv.GRZ AS '保证水位(m)',
       rv.MAIN_RV AS '关联河道'
FROM sl323.st_rvfcch_b rv
JOIN sl323.st_stbprp_b b ON rv.STCD = b.stcd
WHERE rv.WRZ IS NOT NULL
ORDER BY rv.WRZ;
```

**Q8:** 综合查询：当前有多少闸站超警戒水位、哪些泵站正在排水、整体防洪形势。

```sql
SELECT
  (SELECT COUNT(*) FROM sl323.st_river_r r
   JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
   JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_river_r GROUP BY stcd) l ON r.stcd = l.stcd AND r.tm = l.maxTm
   WHERE r.z > rv.WRZ AND rv.WRZ IS NOT NULL) AS '超警戒站点数',
  (SELECT COUNT(*) FROM sl323.st_pump_r p
   WHERE p.pdchcd = '2' AND p.omcn > 0
     AND p.tm = (SELECT MAX(p2.tm) FROM sl323.st_pump_r p2 WHERE p2.stcd = p.stcd)) AS '正在排水泵站数',
  (SELECT SUM(p.pmpq) FROM sl323.st_pump_r p
   WHERE p.pdchcd = '2' AND p.omcn > 0
     AND p.tm = (SELECT MAX(p2.tm) FROM sl323.st_pump_r p2 WHERE p2.stcd = p.stcd)) AS '总排水流量(m³/s)',
  (SELECT COUNT(*) FROM sl323.st_gate_r g
   WHERE g.gtophgt > 0
     AND g.tm = (SELECT MAX(g2.tm) FROM sl323.st_gate_r g2 WHERE g2.stcd = g.stcd)) AS '开启闸门数';
```

**Q9:** 查询当前所有站点的预警状态一览（包含正常站）。

```sql
SELECT b.stnm AS '测站名称', r.z AS '当前水位(m)',
       rv.WRZ AS '警戒水位(m)', rv.GRZ AS '保证水位(m)',
       CASE
         WHEN rv.WRZ IS NULL THEN '未配置预警'
         WHEN r.z > rv.GRZ THEN '红色预警'
         WHEN r.z > rv.WRZ THEN '黄色预警'
         ELSE '正常'
       END AS '预警状态',
       r.tm AS '更新时间'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
LEFT JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_river_r GROUP BY stcd) latest
  ON r.stcd = latest.stcd AND r.tm = latest.maxTm
ORDER BY CASE WHEN r.z > rv.GRZ THEN 1 WHEN r.z > rv.WRZ THEN 2 ELSE 3 END, r.z DESC;
```

**Q10:** 查询最近30天内是否有站点曾超警戒水位。

```sql
SELECT b.stnm AS '测站名称', r.z AS '水位(m)', rv.WRZ AS '警戒水位(m)',
       r.tm AS '时间',
       CASE WHEN r.z > rv.GRZ THEN '超保证' WHEN r.z > rv.WRZ THEN '超警戒' END AS '预警类型'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
WHERE r.tm >= DATE_SUB(NOW(), INTERVAL 30 DAY)
  AND r.z > rv.WRZ
  AND rv.WRZ IS NOT NULL
ORDER BY r.z - rv.WRZ DESC;
```

**Q11:** 扬州市重点河道（古运河、新城河、瘦西湖、沿山河等）实时水位情况。

```sql
SELECT b.stnm AS '测站名称', r.z AS '实时水位(m)', r.tm AS '更新时间',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN rv.WRZ IS NOT NULL AND r.z > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
FROM sl323.st_river_r r
INNER JOIN (
  SELECT r.stcd, b.stnm, MAX(tm) AS maxTm
  FROM sl323.st_river_r r
  INNER JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
  WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）',
                    '七里河水位站（东花园路）', '赵家支沟水文站（赵家河路）', '瘦西湖水位站')
     OR b.rvnm IN ('沿山河')
  GROUP BY r.stcd, b.stnm
) sub ON r.stcd = sub.stcd AND r.tm = sub.maxTm
LEFT JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD;
```

**Q12:** 查询所有水质站的最新水质综合评级，标注低于Ⅲ类的站点。

```sql
SELECT b.stnm AS '测站', d.spt AS '采样时间',
       d.codmn AS 'CODMn', d.dox AS 'DO', d.nh3n AS 'NH3N', d.tp AS 'TP',
       CASE
         WHEN d.codmn > 15 OR d.dox < 2 OR d.nh3n > 2 OR d.tp > 0.4 THEN '劣Ⅴ类'
         WHEN d.codmn > 10 OR d.dox < 3 OR d.nh3n > 1.5 OR d.tp > 0.3 THEN 'Ⅴ类'
         WHEN d.codmn > 6 OR d.dox < 5 OR d.nh3n > 1 OR d.tp > 0.2 THEN 'Ⅳ类'
         WHEN d.codmn > 4 OR d.dox < 6 OR d.nh3n > 0.5 OR d.tp > 0.1 THEN 'Ⅲ类'
         WHEN d.codmn > 2 OR d.dox < 7.5 OR d.nh3n > 0.15 OR d.tp > 0.02 THEN 'Ⅱ类'
         ELSE 'Ⅰ类'
       END AS '综合评级',
       CASE
         WHEN d.codmn > 6 OR d.dox < 5 OR d.nh3n > 1 OR d.tp > 0.2 THEN '水质异常'
         ELSE '正常'
       END AS '预警'
FROM sl325.wq_pcp_d d
JOIN sl323.st_stbprp_b b ON d.stcd = b.stcd
WHERE b.sttp = 'WQ'
  AND d.spt = (SELECT MAX(d2.spt) FROM sl325.wq_pcp_d d2 WHERE d2.stcd = d.stcd)
ORDER BY d.codmn DESC;
```

**Q13:** 2024年8月扬州城区降雨量最大的那天，各重点河道水位是否超警戒？

```sql
SELECT b.stnm AS '测站名称',
       MAX(CASE WHEN r.tm BETWEEN '2024-08-17' AND '2024-08-23' THEN r.z END) AS '期间最高水位(m)',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN MAX(CASE WHEN r.tm BETWEEN '2024-08-17' AND '2024-08-23' THEN r.z END) > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
FROM sl323.st_stbprp_b b
JOIN sl323.st_river_r r ON b.stcd = r.stcd
LEFT JOIN sl323.st_rvfcch_b rv ON b.stcd = rv.STCD
WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）',
                  '七里河水位站（东花园路）', '赵家支沟水文站（赵家河路）', '瘦西湖水位站')
  AND r.tm BETWEEN '2024-08-01' AND '2024-08-31'
GROUP BY b.stnm, rv.WRZ;
```

**Q14:** 查询历史上超保证水位（GRZ）的站点及出现时间。

```sql
SELECT b.stnm AS '测站名称', r.z AS '水位(m)', rv.GRZ AS '保证水位(m)',
       r.tm AS '时间', rv.GRZ AS '保证水位'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
JOIN sl323.st_rvfcch_b rv ON r.stcd = rv.STCD
WHERE r.z > rv.GRZ AND rv.GRZ IS NOT NULL
ORDER BY r.z - rv.GRZ DESC
LIMIT 20;
```

---

## 按难度汇总

| Skill | L1(简单) | L2(中等) | L3(复杂) | 合计 |
|-------|---------|---------|---------|------|
| water-situation | 4 | 6 | 15 | 25 |
| rainfall | 3 | 3 | 12 | 18 |
| water-quality | 2 | 3 | 8 | 13 |
| water-forecast | 2 | 3 | 8 | 13 |
| gate-pump-operation | 2 | 3 | 10 | 15 |
| water-warning | 2 | 3 | 9 | 14 |
| **合计** | **15** | **21** | **62** | **98** |

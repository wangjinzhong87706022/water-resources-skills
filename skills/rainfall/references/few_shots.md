# 雨情 Few-Shot 示例

> 来源: /home/scada/dataagent/domains/sqls.txt 原始 Question-SQL 对

> **⚠️ 时间锚点警示**：所有示例中的"最新/最近"都必须锚 `MAX(tm)`（或 f_rnfl_h 的 `MAX(FYMDH)`），禁锚 NOW()/CURDATE()（库数据滞后于挂钟，实测停在 2026-06）。相关/无界 MAX 子查询必须带时间范围裁剪；年度统计用半开区间 `tm >= '20XX-01-01' AND tm < '20XX+1-01-01'`。

## 实时降雨

### Q: 24年扬州城区降雨总量大概是多少？哪天降雨最大？

```sql
SELECT
  (SELECT SUM(drp) FROM st_pptn_r
   WHERE stcd = '58245' AND tm >= '2024-01-01' AND tm < '2025-01-01' AND drp IS NOT NULL) AS 扬州城区2024年总降雨量,
  (SELECT DATE(tm) FROM st_pptn_r
   WHERE stcd = '58245' AND tm >= '2024-01-01' AND tm < '2025-01-01'
   GROUP BY DATE(tm) ORDER BY SUM(drp) DESC LIMIT 1) AS 最大降雨日期,
  (SELECT SUM(drp) FROM st_pptn_r
   WHERE stcd = '58245' AND tm >= '2024-01-01' AND tm < '2025-01-01'
   GROUP BY DATE(tm) ORDER BY SUM(drp) DESC LIMIT 1) AS 最大日降雨量;
```

### Q: 24年扬州城区哪天降雨量最大

```sql
SELECT DATE(p.tm) AS '日期', SUM(p.drp) AS '总降水量(mm)'
FROM st_pptn_r p JOIN st_stbprp_b b ON p.stcd = b.stcd
WHERE b.stcd = '58245'
  AND p.tm >= '2024-01-01' AND p.tm < '2025-01-01' AND p.drp IS NOT NULL
GROUP BY DATE(p.tm) ORDER BY SUM(p.drp) DESC LIMIT 1;
```

### Q: 2024年扬州各区域累计降雨量最高的前三个区域

```sql
SELECT p.addvcd AS '行政区划码', AVG(p.drp) AS '累计降水量(mm)'
FROM (
  SELECT b.addvcd, b.stcd, SUM(p.drp) AS drp
  FROM st_pptn_r p JOIN st_stbprp_b b ON p.stcd = b.stcd
  WHERE p.tm >= '2024-01-01' AND p.tm < '2025-01-01'
    AND p.drp IS NOT NULL AND b.addvcd IS NOT NULL AND b.addvcd != ''
  GROUP BY b.addvcd, b.stcd
) p
GROUP BY p.addvcd ORDER BY AVG(p.drp) DESC LIMIT 3;
```

### Q: 某测站最近30天降雨数据

```sql
SELECT DATE(p.tm) AS '日期', SUM(p.drp) AS '日降雨量(mm)'
FROM st_pptn_r p JOIN st_stbprp_b b ON p.stcd = b.stcd
WHERE b.stnm LIKE '%某站%'
  AND p.tm > DATE_SUB((SELECT MAX(tm) FROM sl323.st_pptn_r), INTERVAL 30 DAY) AND p.drp IS NOT NULL
GROUP BY DATE(p.tm) ORDER BY DATE(p.tm);
```

## 降雨预报

### Q: 查询扬州城区最新短临降雨预报

```sql
-- 注意：MAX(FYMDH) 子查询必须限定近期范围，避免全分区扫描。
-- FYMDH 若为 datetime 类型可如下用 DATE_SUB 裁剪；若实际为字符串编码（如 'YYYYMMDDHH'），改用同格式的字符串下界比较。
SELECT h.YMDH AS '预报时刻', h.RN AS '预报降雨量(mm)', h.FYMDH AS '发布时间'
FROM f_rnfl_h h
JOIN f_rnfl_info_r i ON i.id = h.ID
WHERE h.UNITNAME = '2' AND h.TYPE = '2'
  AND i.adcd_name = '扬州城区'
  AND h.FYMDH = (SELECT MAX(FYMDH) FROM f_rnfl_h
                 WHERE UNITNAME = '2' AND TYPE = '2'
                   AND FYMDH > DATE_SUB((SELECT MAX(FYMDH) FROM f_rnfl_h), INTERVAL 30 DAY))
ORDER BY h.YMDH;
```

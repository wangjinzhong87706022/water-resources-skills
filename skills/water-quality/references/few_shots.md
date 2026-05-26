# 水质 Few-Shot 示例

> 来源: /home/scada/dataagent/domains/sqls.txt 原始 Question-SQL 对

## 水质监测

### Q: 最近一个月瘦西湖水质变化趋势

```sql
SELECT DATE(spt) AS 日期,
       AVG(dox) AS 平均溶解氧, AVG(codmn) AS 平均高锰酸盐指数,
       AVG(wtmp) AS 平均水温, AVG(ph) AS 平均pH值,
       AVG(nh3n) AS 平均氨氮, AVG(turb) AS 平均浊度, AVG(tp) AS 平均总磷
FROM sl325.wq_pcp_d
INNER JOIN sl323.st_stbprp_b b ON wq_pcp_d.stcd = b.stcd
WHERE b.stnm LIKE '%瘦西湖%' AND b.sttp = 'WQ'
  AND spt >= DATE_SUB(NOW(), INTERVAL 1 MONTH) AND spt <= NOW()
GROUP BY DATE(spt) ORDER BY DATE(spt);
```

**注意:** wq_pcp_d 在 sl325 库，时间字段是 **spt** 不是 tm。

## 水质预测与评级

### Q: 预测未来24小时瘦西湖水质指标值、评级值以及最终水质评价值

```sql
SELECT stnm AS 测站, tm AS 预报时间,
       codmn AS 高锰酸盐指数, dox AS 溶解氧, nh3n AS 氨氮, tp AS 总磷,
       codmn_rating AS 高锰酸盐评级, dox_rating AS 溶解氧评级,
       nh3n_rating AS 氨氮评级, tp_rating AS 总磷评级,
       CASE
         WHEN '劣Ⅴ类' IN (codmn_rating, dox_rating, nh3n_rating, tp_rating) THEN '劣Ⅴ类'
         WHEN 'Ⅴ类' IN (codmn_rating, dox_rating, nh3n_rating, tp_rating) THEN 'Ⅴ类'
         WHEN 'Ⅳ类' IN (codmn_rating, dox_rating, nh3n_rating, tp_rating) THEN 'Ⅳ类'
         WHEN 'Ⅲ类' IN (codmn_rating, dox_rating, nh3n_rating, tp_rating) THEN 'Ⅲ类'
         WHEN 'Ⅱ类' IN (codmn_rating, dox_rating, nh3n_rating, tp_rating) THEN 'Ⅱ类'
         ELSE 'Ⅰ类'
       END AS 最终水质评级
FROM (
  SELECT tm, stnm, codmn, dox, nh3n, tp,
         CASE WHEN codmn <= 2 THEN 'Ⅰ类' WHEN codmn <= 4 THEN 'Ⅱ类'
              WHEN codmn <= 6 THEN 'Ⅲ类' WHEN codmn <= 10 THEN 'Ⅳ类'
              WHEN codmn <= 15 THEN 'Ⅴ类' ELSE '劣Ⅴ类' END AS codmn_rating,
         CASE WHEN dox >= 7.5 THEN 'Ⅰ类' WHEN dox BETWEEN 6 AND 7.5 THEN 'Ⅱ类'
              WHEN dox BETWEEN 5 AND 6 THEN 'Ⅲ类' WHEN dox BETWEEN 3 AND 5 THEN 'Ⅳ类'
              WHEN dox BETWEEN 2 AND 3 THEN 'Ⅴ类' ELSE '劣Ⅴ类' END AS dox_rating,
         CASE WHEN nh3n <= 0.15 THEN 'Ⅰ类' WHEN nh3n <= 0.5 THEN 'Ⅱ类'
              WHEN nh3n <= 1 THEN 'Ⅲ类' WHEN nh3n <= 1.5 THEN 'Ⅳ类'
              WHEN nh3n <= 2 THEN 'Ⅴ类' ELSE '劣Ⅴ类' END AS nh3n_rating,
         CASE WHEN tp <= 0.02 THEN 'Ⅰ类' WHEN tp <= 0.1 THEN 'Ⅱ类'
              WHEN tp <= 0.2 THEN 'Ⅲ类' WHEN tp <= 0.3 THEN 'Ⅳ类'
              WHEN tp <= 0.4 THEN 'Ⅴ类' ELSE '劣Ⅴ类' END AS tp_rating
  FROM (
    SELECT tm, b.stnm,
           MAX(CASE WHEN type = 104 THEN (SELECT value FROM slztk.wq_cod_pz WHERE min <= vals AND max > vals) END) AS codmn,
           MAX(CASE WHEN type = 103 THEN vals END) AS dox,
           MAX(CASE WHEN type = 128 THEN vals END) AS nh3n,
           MAX(CASE WHEN type = 105 THEN vals END) AS tp
    FROM slztk.st_mx_preset_r_shj_auto r
    INNER JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
    WHERE sttp = 'WQ' AND b.stnm LIKE '%瘦西湖%'
      AND type IN (104, 103, 128, 105)
      AND tm BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
      AND taskid = (SELECT taskid FROM slztk.st_mx_taskid_shj_auto ORDER BY tm DESC LIMIT 1)
    GROUP BY tm, stnm
  ) AS sub
) AS final ORDER BY tm;
```

**注意:**
- st_mx_preset_r_shj_auto 和 wq_cod_pz 在 **slztk** 库
- st_stbprp_b 在 **sl323** 库
- 跨库查询需带库名前缀
- type 是 **int** 类型（103/104/105/128）

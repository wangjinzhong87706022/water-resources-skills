# 水情 Few-Shot 示例

> 来源: /home/scada/dataagent/domains/sqls.txt 原始 Question-SQL 对

## 河道水位

> ⚠️ **写 SQL 前先看这条反例。** 提到具体测站名(宝应/白马闸/古运河)时,要么单条 SQL 按名 JOIN,要么用下方「标准三件套」在同一脚本内实值代入。**不要**跨回合留 `stcd='{stcd}'`、`DATE(tm)='{dt}'` 这种未填值的占位符——会匹配 0 行。相对时间窗锚定 `MAX(tm)`(库数据滞后,锚 `CURDATE()` 常落空),且不要写窄(30 天≠单天)。
>
> ❌ 错(占位符污染,0 行): `WHERE stcd='{stcd}' AND DATE(tm)='{dt}'`
> ✅ 对(按名 JOIN + MAX(tm) 锚定): `JOIN st_stbprp_b b ON r.stcd=b.stcd WHERE b.stnm LIKE '%宝应%' AND r.tm > DATE_SUB((SELECT MAX(tm) FROM st_river_r), INTERVAL 30 DAY)`

### 标准三件套（一轮完成：站点识别 + MAX(tm) 锚定 + 聚合主查询）

"X 站/X 河最近 N 天(月)水位数据/情况/趋势"类问题**照抄此模板**，一个脚本一轮跑完，禁止拆成多个回合：

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

name, days = '宝应', 30   # ← 只改这两处

# 1) 站点识别（stnm+rvnm 双匹配）
stations = query(f"SELECT DISTINCT stcd, stnm, sttp, rvnm, dtmnm FROM st_stbprp_b "
                 f"WHERE (stnm LIKE '%{name}%' OR rvnm LIKE '%{name}%')")
assert stations, '无匹配站，剥核心词回退（见 SKILL.md 同族站规则）'
in_list = "','".join(sorted({r['stcd'] for r in stations}))

# 2) 新鲜度探测（PK 索引，毫秒级；锚定 MAX(tm) 而非 CURDATE）
anchor = query(f"SELECT MAX(tm) AS mt FROM st_river_r WHERE stcd IN ('{in_list}')")[0]['mt']
assert anchor, '目标站在 st_river_r 无数据，回退同族站（见 SKILL.md）'

# 3) 主查询：总体统计 + 日均序列（聚合优先，不拉原始行）
win = (f"r.stcd IN ('{in_list}') AND r.z IS NOT NULL "
       f"AND r.tm > DATE_SUB('{anchor}', INTERVAL {days} DAY) AND r.tm <= '{anchor}'")
stats = query(f"SELECT b.stnm AS 测站, COUNT(*) AS 条数, ROUND(AVG(r.z),2) AS 平均水位, "
              f"ROUND(MAX(r.z),2) AS 最高水位, ROUND(MIN(r.z),2) AS 最低水位 "
              f"FROM st_river_r r JOIN st_stbprp_b b ON r.stcd=b.stcd WHERE {win} GROUP BY b.stnm")
daily = query(f"SELECT DATE(r.tm) AS 日期, ROUND(AVG(r.z),2) AS 日均水位, ROUND(MAX(r.z),2) AS 日最高, "
              f"ROUND(MIN(r.z),2) AS 日最低 FROM st_river_r r WHERE {win} GROUP BY DATE(r.tm) ORDER BY 日期")
print('数据截止:', anchor); print(stats); print(daily)
```

答复中注明"数据截止 {anchor}"。跨月/跨年对比只需把 win 换成 `tm` 连续区间（分区裁剪，禁 `YEAR(tm) IN`）。

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
-- 注: 求"最高水位出现时间"必须按 max_z 回表定位 tm——`MAX(tm)` 是窗口内最晚时刻,不是最高水位时刻
-- 时间窗用半开区间(BETWEEN 的 datetime 上界会丢掉末日整天数据)
SELECT b.stnm AS 测站名称, r.z AS 最高水位, r.tm AS 出现时间,
       rv.WRZ AS 警戒水位,
       CASE WHEN r.z > rv.WRZ THEN '是' ELSE '否' END AS 是否超标
FROM st_river_r r
INNER JOIN (
  SELECT stcd, MAX(z) AS max_z
  FROM st_river_r WHERE tm >= '2024-08-17' AND tm < '2024-08-24' GROUP BY stcd
) sub ON r.stcd = sub.stcd AND r.z = sub.max_z
INNER JOIN st_stbprp_b b ON r.stcd = b.stcd
INNER JOIN st_rvfcch_b rv ON r.stcd = rv.STCD
WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）', '瘦西湖水位站')
  AND r.tm >= '2024-08-17' AND r.tm < '2024-08-24';
```

### Q: 水位站宝应最近30天水位数据

```sql
SELECT r.tm AS '时间', r.z AS '水位(m)'
FROM st_river_r r JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%宝应%'
  AND r.tm > DATE_SUB((SELECT MAX(tm) FROM st_river_r), INTERVAL 30 DAY) AND r.z IS NOT NULL
ORDER BY r.tm;
```

> 更优做法见顶部「标准三件套」：日聚合输出而非逐条原始行。

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
WHERE b.addvcd LIKE '3210%'
  AND r.tm > DATE_SUB((SELECT MAX(tm) FROM st_river_r), INTERVAL 1 HOUR)
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

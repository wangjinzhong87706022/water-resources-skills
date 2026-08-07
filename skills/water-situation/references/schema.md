# 水情 Schema

> 来源: 实际 MySQL DDL (192.168.100.103)

## sl323.st_river_r — 河道水情表

按时间 RANGE 分区 (p2023~p2026)

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(18) NOT NULL | 测站编码 (PK) |
| tm | datetime NOT NULL | 时间 (PK) |
| z | decimal(38,3) | 水位 (m) |
| q | decimal(38,3) | 流量 (m³/s) |
| xsa | decimal(38,3) | 断面过水面积 |
| xsavv | decimal(38,3) | 断面平均流速 |
| xsmxv | decimal(38,3) | 断面最大流速 |
| flwchrcd | char(1) | 河水特征码 |
| wptn | char(1) | 水势: 4=涨, 5=落, 6=平 |
| msqmt | char(1) | 测流方法 |
| msamt | char(1) | 测积方法 |
| msvmt | char(1) | 测速方法 |

**PK:** (stcd, tm)

---

### S3 场景映射 — st_river_r

| 适用场景 | 不适用场景 | 典型查询模式 |
|---------|-----------|-------------|
| 查询河道实时/历史水位 | 查询水库水位（用 st_rsvr_r） | `SELECT z FROM st_river_r WHERE stcd = ? AND tm >= ?` |
| 水位趋势分析（涨/落/平 wptn） | 跨年对比（必须带 tm 连续区间） | `SELECT tm, z FROM ... WHERE tm >= '2023-01-01' AND tm < '2025-01-01'` |
| 月度/年度水位统计（均值、最高、最低） | 水质查询（用 sl325.wq_pcp_d） | `SELECT AVG(z), MAX(z), MIN(z) FROM ... GROUP BY YEAR(tm)` |
| 超警戒判断（联表 st_rvfcch_b） | 降雨量查询（用 st_pptn_r） | `JOIN st_rvfcch_b ON stcd = STCD WHERE z > WRZ` |
| 水位站数量统计（联表 st_stbprp_b） | — | `COUNT(DISTINCT b.stcd) WHERE b.sttp = 'ZZ'` |

**关联表**：st_stbprp_b（测站名称）、st_rvfcch_b（警戒/保证水位）

**高频用例**：
- Q1: 古运河水位测站列表（stnm/rvnm LIKE '%古运河%'）
- Q4: 宝应站最近30天水位（stnm LIKE '%宝应%'）
- Q8: 古运河历史最高/低水位（MAX/MIN(z) GROUP BY stnm）

---

### S5 口径定义 — st_river_r

**字段业务口径**：

| 字段 | 业务含义 | 范围/约束 | 特殊规则 |
|------|---------|----------|---------|
| stcd | 测站编码 | char(18)，与 st_stbprp_b.stcd 一致 | **必须 JOIN st_stbprp_b 按 stnm 查，禁止先查 stcd 再代入**（占位符污染高频坑） |
| tm | 观测时间 | datetime，PK | **RANGE(tm) 分区表，WHERE 必须用连续区间**：`tm >= '2023-01-01' AND tm < '2025-01-01'`。禁止 `YEAR(tm) IN (2023,2024)`（分区裁剪失效，实测 434s 超时） |
| z | 水位 | decimal(38,3) | 范围 **-1 ~ 20m**，超出需标记异常 |
| q | 流量 | decimal(38,3) | 单位 m³/s，部分测站无流量数据（q IS NULL） |
| wptn | 水势编码 | char(1) | **4=涨, 5=落, 6=平**（编码需前置说明） |
| xsa | 断面过水面积 | decimal(38,3) | 单位 m² |
| xsavv | 断面平均流速 | decimal(38,3) | 单位 m/s |

**分区规则（⚠️ 最高频错误）**：
- 分区键：`tm`（RANGE 分区，p2023~p2026）
- 裁剪条件：`WHERE tm >= 'YYYY-MM-DD' AND tm < 'YYYY-MM-DD'`
- **反模式（禁止）**：
  - ❌ `YEAR(tm) = 2024` 或 `YEAR(tm) IN (2023,2024)`
  - ❌ `MONTH(tm) = 8`
  - ❌ `DATE(tm) BETWEEN ...`（函数包裹分区键）
- **正确示例**：
  - ✅ `tm >= '2025-01-01' AND tm < '2026-01-01'`（2025 全年）
  - ✅ `tm BETWEEN '2024-08-01' AND '2024-08-31'`（2024 年 8 月）
  - ✅ `tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)`（最近 30 天）

**编码映射**：
- 河道站 stcd 格式：`3210XXXX`（扬州地区）
- 水库站 stcd 格式：`510BXXXX`（不同编码体系，无法直接 JOIN）

**常见错误示例**：

| 错误写法 | 正确写法 | 错误类型 |
|---------|---------|---------|
| `WHERE YEAR(tm) IN (2023,2024)` | `WHERE tm >= '2023-01-01' AND tm < '2025-01-01'` | 分区超时 |
| `WHERE stcd='{stcd}'` | `JOIN st_stbprp_b b ON r.stcd=b.stcd WHERE b.stnm LIKE '%宝应%'` | 占位符污染 |
| `WHERE b.rvnm='古运河'` | `WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')` | 匹配不全 |

---

### S6 SQL 模板 — st_river_r

**模板 1：按站名查水位（高频，占位符防护）**

```sql
SELECT r.tm AS '时间', r.z AS '水位(m)', r.q AS '流量(m³/s)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%{站名}%'  -- 直接按名查，禁止两步法
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL {天数} DAY)
  AND r.z IS NOT NULL
ORDER BY r.tm;
```

**模板 2：月度/年度统计（分区裁剪合规）**

```sql
SELECT
  YEAR(tm) AS '年份',
  AVG(z) AS '平均水位(m)',
  MAX(z) AS '最高水位(m)',
  MIN(z) AS '最低水位(m)'
FROM sl323.st_river_r
WHERE tm >= '{起始日期}' AND tm < '{结束日期}'  -- 必须连续区间
  AND stcd IN ('{stcd1}', '{stcd2}')  -- 提前查好 stcd
GROUP BY YEAR(tm)
ORDER BY YEAR(tm);
```

**模板 3：水位站数量（按河流统计）**

```sql
SELECT b.rvnm AS '河流名称', COUNT(DISTINCT b.stcd) AS '水位站数量'
FROM sl323.st_stbprp_b b
WHERE b.sttp = 'ZZ' AND b.rvnm IS NOT NULL AND b.rvnm != ''
GROUP BY b.rvnm
ORDER BY COUNT(DISTINCT b.stcd) DESC
LIMIT 10;
```

**模板 4：超警戒判断（联表阈值，含存在性检查）**

```sql
SELECT b.stnm AS '测站名称',
       MAX(r.z) AS '最高水位(m)',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN MAX(r.z) > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
LEFT JOIN sl323.st_rvfcch_b rv ON b.stcd = rv.STCD
WHERE b.stnm LIKE '%{站名}%'
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL {天数} DAY)
  AND rv.WRZ IS NOT NULL  -- 阈值存在性检查前置（GRZ 全表 0%，WRZ 基本为空）
GROUP BY b.stnm, rv.WRZ;
```

**模板 5：跨站对比（含时间窗口）**

```sql
SELECT b.stnm AS '测站名称',
       MAX(CASE WHEN r.tm BETWEEN '{开始日期}' AND '{结束日期}' THEN r.z END) AS '期间最高水位(m)'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.stnm LIKE '%{河道名}%' OR b.rvnm LIKE '%{河道名}%')
  AND r.tm BETWEEN '{开始日期}' AND '{结束日期}'
GROUP BY b.stnm;
```

**模板 6：实时水位（最新记录）**

```sql
SELECT b.stnm AS '测站名称',
       r.z AS '实时水位(m)',
       r.tm AS '更新时间',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN r.z > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
LEFT JOIN sl323.st_rvfcch_b rv ON b.stcd = rv.STCD
WHERE b.stnm LIKE '%{站名}%'
  AND r.tm = (SELECT MAX(tm) FROM sl323.st_river_r WHERE stcd = b.stcd)  -- 最新记录
LIMIT 1;
```

---

## sl323.st_rsvr_r — 水库水情表

| 字段 | 类型 | 含义 |
|------|------|------|
| stcd | char(8) NOT NULL | 测站编码 (PK) |
| tm | datetime NOT NULL | 时间 (PK) |
| rz | decimal(7,3) | 库上水位 (m) |
| inq | decimal(9,3) | 入库流量 (m³/s) |
| w | decimal(9,3) | 蓄水量 (10⁶ m³) |
| blrz | decimal(7,3) | 库下水位 (m) |
| otq | decimal(9,3) | 出库流量 (m³/s) |
| rwchrcd | char(1) | 库水特征码 |
| rwptn | char(1) | 库水水势: 4=涨, 5=落, 6=平 |
| inqdr | decimal(5,2) | 入流时段长 |
| msqmt | char(1) | 测流方法 |

**PK:** (tm, stcd)

---

### S3 场景映射 — st_rsvr_r

| 适用场景 | 不适用场景 | 典型查询模式 |
|---------|-----------|-------------|
| 查询水库实时/历史水位（rz 字段） | 河道水位查询（用 st_river_r） | `SELECT rz, inq, otq FROM st_rsvr_r WHERE stcd = ? AND tm >= ?` |
| 水库蓄水量变化（w 字段，10⁶ m³） | 水质查询（用 sl325.wq_pcp_d） | `SELECT w FROM ... WHERE tm BETWEEN '2024-01-01' AND '2024-12-31'` |
| 入库/出库流量分析（inq/otq） | 降雨量查询（用 st_pptn_r） | `SELECT inq, otq, inq-otq AS 水量差 FROM ...` |
| 库上/库下水位对比（rz/blrz） | 闸站/泵站查询（用 st_was_r/st_pump_r） | `SELECT rz, blrz, rz-blrz AS 水位差 FROM ...` |

**关联表**：st_stbprp_b（测站名称）、st_rsvrfcch_b（库容曲线，**当前为空**）

**高频用例**：
- 水库水位趋势查询
- 入库/出库流量对比
- 蓄水量变化分析

---

### S5 口径定义 — st_rsvr_r

**字段业务口径**：

| 字段 | 业务含义 | 范围/约束 | 特殊规则 |
|------|---------|----------|---------|
| stcd | 测站编码 | char(8)，与 st_stbprp_b.stcd 一致 | 水库站 stcd 格式：`510BXXXX`，与河道站（3210XXXX）不同 |
| tm | 观测时间 | datetime，PK | **RANGE(tm) 分区表**，WHERE 必须用连续区间：`tm >= '2023-01-01' AND tm < '2025-01-01'` |
| rz | 库上水位 | decimal(7,3) | 单位 m，范围 -1 ~ 50m（水库水位通常高于河道） |
| inq | 入库流量 | decimal(9,3) | 单位 m³/s |
| w | 蓄水量 | decimal(9,3) | 单位 10⁶ m³（百万立方米） |
| blrz | 库下水位 | decimal(7,3) | 单位 m |
| otq | 出库流量 | decimal(9,3) | 单位 m³/s |
| rwchrcd | 库水特征码 | char(1) | 类似河水特征码 |
| rwptn | 库水水势 | char(1) | **4=涨, 5=落, 6=平** |
| inqdr | 入流时段长 | decimal(5,2) | 单位 小时 |

**分区规则（⚠️ 同 st_river_r）**：
- 分区键：`tm`（RANGE 分区）
- 裁剪条件：`WHERE tm >= 'YYYY-MM-DD' AND tm < 'YYYY-MM-DD'`
- 反模式：同 st_river_r（禁止 YEAR(tm)/MONTH(tm) 等函数包裹分区键）

**数据特殊性**：
- ⚠️ **水库数据可能非常稀疏**：st_rsvr_r 表可能仅有最近 1 天的数据（如仅 2025-05-19），远少于河道水情
- ⚠️ **历史流量数据可能为空**：inq/otq 历史数据可能全为空
- **查询前应先用**：`SELECT MIN(tm), MAX(tm), COUNT(*) FROM st_rsvr_r WHERE rz IS NOT NULL` 确认实际数据范围
- **查询前应确认字段非空**：`SELECT COUNT(*) FROM st_rsvr_r WHERE inq IS NOT NULL`

**水库相关表大多为空**：
- st_rsvrfcch_b（库容曲线）、st_rsvrfcch_b（防洪参数）、st_rsvrav_r、st_rsvrevs_r（蒸发）在 2025-05 均为空表
- **无法查询水库汛限水位**（st_rsvrfcch_b 为空，无相关字段）

---

### S6 SQL 模板 — st_rsvr_r

**模板 1：水库水位趋势（带分区裁剪）**

```sql
SELECT tm AS '时间', rz AS '库上水位(m)', blrz AS '库下水位(m)',
       w AS '蓄水量(10⁶m³)', inq AS '入库流量(m³/s)', otq AS '出库流量(m³/s)'
FROM sl323.st_rsvr_r
WHERE stcd = '{水库站编码}'
  AND tm >= DATE_SUB(CURDATE(), INTERVAL {天数} DAY)
  AND rz IS NOT NULL
ORDER BY tm;
```

**模板 2：蓄水量变化分析（需先确认数据存在性）**

```sql
-- Step 1: 确认数据存在性
SELECT MIN(tm), MAX(tm), COUNT(*) FROM sl323.st_rsvr_r WHERE w IS NOT NULL;

-- Step 2: 查询蓄水量变化（如果 Step 1 有数据）
SELECT DATE_FORMAT(tm, '%Y-%m') AS '月份',
       AVG(w) AS '平均蓄水量(10⁶m³)',
       MAX(w) AS '最大蓄水量',
       MIN(w) AS '最小蓄水量'
FROM sl323.st_rsvr_r
WHERE stcd = '{水库站编码}'
  AND tm BETWEEN '{起始日期}' AND '{结束日期}'
  AND w IS NOT NULL
GROUP BY DATE_FORMAT(tm, '%Y-%m')
ORDER BY DATE_FORMAT(tm, '%Y-%m');
```

**模板 3：入库/出库流量对比（需先确认字段非空）**

```sql
-- Step 1: 确认 inq/otq 有数据
SELECT COUNT(*) FROM sl323.st_rsvr_r WHERE inq IS NOT NULL OR otq IS NOT NULL;

-- Step 2: 查询流量对比（如果 Step 1 > 0）
SELECT tm AS '时间', inq AS '入库流量(m³/s)', otq AS '出库流量(m³/s)',
       (inq - otq) AS '水量差(m³/s)'
FROM sl323.st_rsvr_r
WHERE stcd = '{水库站编码}'
  AND tm >= DATE_SUB(CURDATE(), INTERVAL {天数} DAY)
  AND (inq IS NOT NULL OR otq IS NOT NULL)
ORDER BY tm;
```

---

## sl323.st_stbprp_b — 测站基础信息表

共 34 个字段（2026-06-29 据库全列核实）：

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

---

### S3 场景映射 — st_stbprp_b

| 适用场景 | 不适用场景 | 典型查询模式 |
|---------|-----------|-------------|
| 测站属性查询（名称/河流/水系/流域/站类） | 水位数据查询（联表 st_river_r） | `SELECT stnm, rvnm, hnnm, bsnm FROM st_stbprp_b WHERE stnm LIKE '%宝应%'` |
| 按站名/河名筛选测站 | 水质数据查询（联表 sl325.wq_pcp_d） | `SELECT * FROM st_stbprp_b WHERE (stnm LIKE '%古运河%' OR rvnm LIKE '%古运河%') AND sttp = 'ZZ'` |
| 测站类型统计（按 sttp 分组） | 水库水位查询（联表 st_rsvr_r） | `SELECT sttp, COUNT(*) FROM st_stbprp_b GROUP BY sttp` |
| 重点河道映射（查询指定测站名称） | 降雨量查询（联表 st_pptn_r） | `SELECT stnm FROM st_stbprp_b WHERE stnm IN ('古运河水位站（新城河口）', ...)` |

**关联表**：所有水情表（st_river_r/st_rsvr_r/st_pptn_r 等）都通过 stcd 关联

**高频用例**：
- Q1: 古运河水位测站列表（(stnm LIKE '%古运河%' OR rvnm LIKE '%古运河%') AND sttp = 'ZZ'）
- Q2: 宝应站所属河流/水系/流域/站类（**需 SELECT stnm, rvnm, hnnm, bsnm, sttp**）
- Q5: 古运河水位数（COUNT(*) WHERE (stnm LIKE '%古运河%' OR rvnm LIKE '%古运河%') AND sttp = 'ZZ'）

---

### S5 口径定义 — st_stbprp_b

> ⚠️ **硬规则（按河道名查测站，违反必返 0 行）**：运河/河道站的 `rvnm` 字段**经常为 NULL**（实测古运河 3 个水位站 rvnm 全为 NULL，仅 stnm 含"古运河"）。**禁止**只用 `WHERE rvnm LIKE '%X%'`，**必须**双匹配：
> ```sql
> WHERE (stnm LIKE '%{河道名}%' OR rvnm LIKE '%{河道名}%')
> ```
> 这条规则覆盖 Q1/Q5/Q8/Q11/Q12/Q14/Q25 等所有"古运河/X 河"类查询。

**字段业务口径（高频查询字段）**：

| 字段 | 业务含义 | 范围/约束 | 特殊规则 |
|------|---------|----------|---------|
| stcd | 测站编码 | char(18)，与各水情表 PK 一致 | **PK 是 (stcd, sttp)，不是单独 stcd**。跨表 JOIN 时直接使用 stcd |
| stnm | 测站名称 | char(30) | **最常用查询字段**：`WHERE stnm LIKE '%{站名}%'` 或 `stnm = '{精确名称}'` |
| rvnm | 河流名称 | char(30) | 水体分类依据（洪泽湖=湖泊、长江=天然河流、里运河=人工运河），详见 water_classification.md |
| hnnm | 水系名称 | char(30) | 如"长江水系" |
| bsnm | 流域名称 | char(30) | 如"长江流域" |
| sttp | 站类 | char(2) | **ZZ=水位站, ZQ=水文站, RR=水库站, DD=闸站, DP=泵站, PP=雨量站, WQ=水质站** |
| addvcd | 行政区划码 | char(6) | 扬州地区以 **3210xx** 开头，非扬州站点（如三岔水库）可能无数据 |
| dtmnm | 基面名称 | char(16) | 高程基准（废黄河口/冻结(吴淞)），详见 elevation_datum.md |
| dtmel | 基面高程 | decimal(7,3) | 单位 m，可能为 NULL |
| lgtd | 经度 | decimal(10,6) | 单位 ° |
| lttd | 纬度 | decimal(10,6) | 单位 ° |

**高频查询模式**：

| 查询意图 | SQL 模式 |
|---------|---------|
| 按站名查属性 | `SELECT stnm, rvnm, hnnm, bsnm, sttp FROM st_stbprp_b WHERE stnm LIKE '%{站名}%'` |
| 按河流查测站 | `SELECT stnm, sttp FROM st_stbprp_b WHERE (stnm LIKE '%{河流名}%' OR rvnm LIKE '%{河流名}%') AND sttp = 'ZZ'` |
| 测站类型统计 | `SELECT sttp, COUNT(*) FROM st_stbprp_b GROUP BY sttp` |
| 重点河道映射 | `SELECT stnm FROM st_stbprp_b WHERE stnm IN ('古运河水位站（新城河口）', ...)` |

**Q2 低分用例专项说明**：
- **问题**：查询宝应水位站的所属河流、水系、流域、测站类别
- **期望 SQL**：
  ```sql
  SELECT stnm AS '测站名称',
         rvnm AS '所属河流',
         hnnm AS '所属水系',
         bsnm AS '所属流域',
         sttp AS '测站类别'
  FROM sl323.st_stbprp_b
  WHERE stnm = '宝应';
  ```
- **常见错误（必须避免）**：
  1. ❌ 使用英文别名（`station_name`）→ 必须用中文别名
  2. ❌ 包含 stcd 字段 → **只选 5 个必需字段**：stnm, rvnm, hnnm, bsnm, sttp
  3. ❌ 缺 schema 前缀 → 必须写 `sl323.st_stbprp_b`
  4. ❌ 使用表别名（`b.stnm`）→ **直接使用表名**
  5. ❌ 使用 `LIKE '%宝应%'` → 精确匹配用 `stnm = '宝应'`
- **S5 强制规则**：用户问"XX站的所属 X"时，SELECT 列表**严格限定为**：测站名称+所属河流+所属水系+所属流域+测站类别，**不得多选**

---

### S6 SQL 模板 — st_stbprp_b

**模板 1：按站名查属性（解决 Q2 低分问题）**

```sql
-- 用户问"XX站的所属河流、水系、流域、测站类别"
SELECT stnm AS '测站名称',
       rvnm AS '所属河流',
       hnnm AS '所属水系',
       bsnm AS '所属流域',
       sttp AS '测站类别'
FROM sl323.st_stbprp_b
WHERE stnm LIKE '%{站名}%'
LIMIT 5;
```

**模板 2：按河流查水位站**

```sql
SELECT stnm AS '测站名称',
       sttp AS '测站类型',
       rvnm AS '所属河流',
       addvcd AS '行政区划码'
FROM sl323.st_stbprp_b
WHERE (stnm LIKE '%{河流名}%' OR rvnm LIKE '%{河流名}%')
  AND sttp IN ('ZZ', 'ZQ')  -- 水位站或水文站
ORDER BY stnm
LIMIT 20;
```

**模板 3：测站类型统计**

```sql
SELECT sttp AS '测站类型',
       COUNT(*) AS '数量',
       GROUP_CONCAT(DISTINCT sttp) AS '类型编码列表'
FROM sl323.st_stbprp_b
GROUP BY sttp
ORDER BY COUNT(*) DESC;
```

**模板 4：重点河道映射**

```sql
-- 根据业务规则映射文件（business_rules.md）查指定测站
SELECT stnm AS '测站名称',
       stcd AS '测站编码',
       sttp AS '测站类型',
       rvnm AS '所属河流'
FROM sl323.st_stbprp_b
WHERE stnm IN ('古运河水位站（新城河口）',
               '新城河水文站（兴城西路北）',
               '七里河水位站（东花园路）',
               '瘦西湖水位站')
ORDER BY stnm;
```

---

## sl323.st_rvfcch_b — 河道站防洪指标表

共 34 个字段（2026-06-29 据库全列核实）：

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

## sl323.st_rvfcch_b — 河道站防洪指标表

共 36 个字段（2026-06-29 据库全列核实）：

| 字段 | 类型 | 含义 |
|------|------|------|
| STCD | varchar(18) NOT NULL | 测站编码（注意大写） |
| LDKEL | decimal(7,3) | 左堤高程 (m) |
| RDKEL | decimal(7,3) | 右堤高程 (m) |
| WRZ | decimal(7,3) | 警戒水位 (m) |
| WRQ | decimal(9,3) | 警戒流量 (m³/s) |
| GRZ | decimal(7,3) | 保证水位 (m) |
| GRQ | decimal(9,3) | 保证流量 (m³/s) |
| FLPQ | decimal(9,3) | 平滩流量 (m³/s) |
| OBHTZ | decimal(7,3) | 实测最高水位 (m) |
| OBHTZTM | datetime | 实测最高水位出现时间 |
| IVHZ | decimal(7,3) | 调查最高水位 (m) |
| IVHZTM | datetime | 调查最高水位出现时间 |
| OBMXQ | decimal(9,3) | 实测最大流量 (m³/s) |
| OBMXQTM | datetime | 实测最大流量出现时间 |
| IVMXQ | decimal(9,3) | 调查最大流量 (m³/s) |
| IVMXQTM | datetime | 调查最大流量出现时间 |
| HMXS | decimal(9,3) | 历史最大含沙量 (kg/m³) |
| HMXSTM | datetime | 历史最大含沙量出现时间 |
| HMXAVV | decimal(9,3) | 历史最大断面平均流速 (m/s) |
| HMXAVVTM | datetime | 历史最大断面平均流速出现时间 |
| HLZ | decimal(7,3) | 历史最低水位 (m) |
| HLZTM | datetime | 历史最低水位出现时间 |
| HMNQ | decimal(9,3) | 历史最小流量 (m³/s) |
| HMNQTM | datetime | 历史最小流量出现时间 |
| TAZ | decimal(7,3) | 高水位告警值 (m) |
| TAQ | decimal(9,3) | 大流量告警值 (m³/s) |
| LAZ | decimal(7,3) | 低水位告警值 (m) |
| LAQ | decimal(9,3) | 小流量告警值 (m³/s) |
| SFZ | decimal(7,3) | 启动预报水位标准 (m) |
| SFQ | decimal(9,3) | 启动预报流量标准 (m³/s) |
| MODITIME | datetime | 时间戳 |
| MAIN_RV | varchar(255) | 关联河道中重要河道 |
| EXTEND_STTP | char(2) | 扩展字段-类型 |
| EXTEND_STSW | decimal(9,3) | 扩展字段-生态水位 |
| EXTEND_UWRZ | varchar(255) | 扩展字段-闸上警戒水位 |
| EXTEND_DWRZ | varchar(255) | 扩展字段-闸下警戒水位 |

**无 PRIMARY KEY；据 INFORMATION_SCHEMA 该表所有列均无索引（STCD 也无索引）** — 所有 JOIN 均为全表扫描。该表仅 231 行，全表扫描可接受。

---

### S3 场景映射 — st_rvfcch_b

| 适用场景 | 不适用场景 | 典型查询模式 |
|---------|-----------|-------------|
| 查询测站防洪指标（警戒/保证水位/流量） | 水位数据查询（用 st_river_r） | `SELECT WRZ, GRZ FROM st_rvfcch_b WHERE STCD = ?` |
| 超警戒/超保证判断（联表 st_river_r） | 水库水位查询（用 st_rsvr_r） | `JOIN st_rvfcch_b ON stcd = STCD WHERE z > WRZ` |
| 历史极值查询（OBHTZ/IVHZ） | 水质数据查询（用 sl325.wq_pcp_d） | `SELECT OBHTZ, OBHTZTM FROM st_rvfcch_b WHERE STCD = ?` |
| 预警水位配置查询 | 降雨量查询（用 st_pptn_r） | `SELECT STCD, WRZ, GRZ FROM st_rvfcch_b WHERE WRZ IS NOT NULL` |

**关联表**：st_river_r（水位数据）、st_stbprp_b（测站名称）

**高频用例**：
- Q8: 古运

河历史最高水位（OBHTZ 字段）
- Q14: 超保证水位站点查询（z > GRZ，但 GRZ 全表 0% 有值，需说明）

---

### S5 口径定义 — st_rvfcch_b

**⚠️ 最高频错误：阈值数据严重缺失**

**字段业务口径（重点阈值字段）**：

| 字段 | 业务含义 | 范围/约束 | 数据质量（⚠️ 重点） |
|------|---------|----------|-------------------|
| STCD | 测站编码 | varchar(18)，**大写**（与 st_river_r.stcd 大小写不同） | JOIN 时必须转换大小写：`ON r.stcd = UPPER(rv.STCD)` 或 `ON UPPER(r.stcd) = rv.STCD` |
| WRZ | 警戒水位 | decimal(7,3)，单位 m | **⚠️ 水位站/水文站基本为空**（如蒋坝站 WRZ=NULL），查询前必须验证存在性 |
| WRQ | 警戒流量 | decimal(9,3)，单位 m³/s | 同上 |
| GRZ | 保证水位 | decimal(7,3)，单位 m | **❌ 全表 0% 有值**，无法用于超保证判断 |
| GRQ | 保证流量 | decimal(9,3)，单位 m³/s | 同上 |
| FLPQ | 平滩流量 | decimal(9,3)，单位 m³/s | — |
| OBHTZ | 实测最高水位 | decimal(7,3)，单位 m | 有值，可用于历史极值查询 |
| OBHTZTM | 实测最高水位时间 | datetime | — |
| IVHZ | 调查最高水位 | decimal(7,3)，单位 m | 有值 |
| TAZ | 高水位告警值 | decimal(7,3)，单位 m | — |
| LAZ | 低水位告警值 | decimal(7,3)，单位 m | — |
| SFZ | 启动预报水位标准 | decimal(7,3)，单位 m | — |

**数据质量总结（⚠️ 必须在前置检查中说明）**：

| 指标 | 状态 | 处理方式 |
|------|------|---------|
| **GRZ（保证水位）** | **全表 0% 有值** | **无法查询超保证水位**，必须告知用户 |
| **WRZ（警戒水位）** | **水位站/水文站基本为空** | 查询前必须验证存在性，缺失时跳过超警判断 |
| OBHTZ（实测最高水位） | 有值 | 可用于历史极值查询 |

**STCD 大小写问题（⚠️ 高频 JOIN 错误）**：
- st_river_r.stcd：小写（如 `3210XXX`）
- st_rvfcch_b.STCD：**大写**（如 `3210XXX`）
- **JOIN 时必须转换大小写**：
  - ✅ `ON r.stcd = UPPER(rv.STCD)`
  - ✅ `ON UPPER(r.stcd) = rv.STCD`
  - ❌ `ON r.stcd = rv.STCD`（大小写不匹配，结果为空）

**无索引问题**：
- **该表所有列均无索引**（包括 STCD），全表扫描（231 行，可接受）
- 避免与 st_rvfcch_b 多次 JOIN（如 UNION 多测站），应一次 JOIN 后筛选

---

### S6 SQL 模板 — st_rvfcch_b

**模板 1：阈值存在性检查（前置检查，强制）**

```sql
-- Step 1: 验证该站阈值数据是否存在
SELECT COUNT(*) as cnt,
       SUM(CASE WHEN WRZ IS NOT NULL THEN 1 ELSE 0 END) as wrz_count,
       SUM(CASE WHEN GRZ IS NOT NULL THEN 1 ELSE 0 END) as grz_count
FROM sl323.st_rvfcch_b
WHERE STCD = '{目标站码}'
  AND (WRZ IS NOT NULL OR GRZ IS NOT NULL);

-- 如果 cnt = 0，跳过阈值查询，告知用户"⚠️ 该站阈值数据缺失"
-- 如果 wrz_count = 0，仅能查询 GRZ（但 GRZ 全表 0% 有值，实际也无法查询）
```

**模板 2：超警戒判断（含存在性检查）**

```sql
SELECT b.stnm AS '测站名称',
       r.z AS '当前水位(m)',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN r.z > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
LEFT JOIN sl323.st_rvfcch_b rv ON UPPER(r.stcd) = rv.STCD  -- 注意大小写转换
WHERE b.stnm LIKE '%{站名}%'
  AND r.tm = (SELECT MAX(tm) FROM sl323.st_river_r WHERE stcd = r.stcd)
  AND rv.WRZ IS NOT NULL  -- 阈值存在性检查前置
LIMIT 1;
```

**模板 3：查询测站防洪指标（全字段）**

```sql
SELECT STCD AS '测站编码',
       WRZ AS '警戒水位(m)',
       WRQ AS '警戒流量(m³/s)',
       GRZ AS '保证水位(m)',
       GRQ AS '保证流量(m³/s)',
       FLPQ AS '平滩流量(m³/s)',
       OBHTZ AS '实测最高水位(m)',
       OBHTZTM AS '实测最高水位时间',
       IVHZ AS '调查最高水位(m)',
       TAZ AS '高水位告警值(m)',
       LAZ AS '低水位告警值(m)'
FROM sl323.st_rvfcch_b
WHERE STCD = '{目标站码}'
LIMIT 1;

-- 注意：WRZ/GRZ 可能为 NULL，查询结果需标注"该站阈值数据缺失"
```

**模板 4：历史极值查询（OBHTZ 有值字段）**

```sql
SELECT b.stnm AS '测站名称',
       rv.OBHTZ AS '实测最高水位(m)',
       rv.OBHTZTM AS '实测最高水位时间',
       rv.IVHZ AS '调查最高水位(m)',
       rv.IVHZTM AS '调查最高水位时间'
FROM sl323.st_rvfcch_b rv
JOIN sl323.st_stbprp_b b ON UPPER(rv.STCD) = b.stcd
WHERE b.stnm LIKE '%{站名}%'
  AND (rv.OBHTZ IS NOT NULL OR rv.IVHZ IS NOT NULL)
LIMIT 10;
```

**模板 5：所有有警戒水位的站点（注意 WRZ 基本为空）**

```sql
SELECT b.stnm AS '测站名称',
       rv.STCD AS '测站编码',
       rv.WRZ AS '警戒水位(m)',
       rv.GRZ AS '保证水位(m)'
FROM sl323.st_rvfcch_b rv
JOIN sl323.st_stbprp_b b ON UPPER(rv.STCD) = b.stcd
WHERE rv.WRZ IS NOT NULL  -- WRZ 基本为空，结果集可能很小
ORDER BY rv.WRZ DESC
LIMIT 20;

-- ⚠️ 预期结果：WRZ 有值的站点极少（水位站/水文站基本为空）
-- 如果结果为空，需告知用户"本库阈值数据缺失，无法提供超警戒判断"
```


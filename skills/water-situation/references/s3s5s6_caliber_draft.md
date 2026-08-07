# Water-Situation S3/S5/S6 素材收集（Phase 1）

> 用于生成 S3/S5/S6 的基础信息
> 日期：2026-07-28

## 1. Pitfalls 关键信息提取

### 分区裁剪（最高频错误）
- **表**：st_river_r/st_rsvr_r/st_was_r/st_pump_r/st_pump_pa 都是 RANGE(tm) 分区表
- **错误做法**：`YEAR(tm) IN (2023,2024)`、`MONTH(tm)=8`
- **正确做法**：`tm >= '2023-01-01' AND tm < '2025-01-01'`
- **实测后果**：434 秒超时

### 占位符污染（高频错误）
- **错误做法**：`WHERE stcd='{stcd}' AND DATE(tm)='{dt}'`
- **正确做法**：`JOIN st_stbprp_b b ON r.stcd=b.stcd WHERE b.stnm LIKE '%宝应%'`
- **触发场景**：题目提到具体测站名时必须直查，禁止两步法

### 水体分类不一致（高频错误）
- rvnm 字段不区分水体类型：洪泽湖（湖泊）、长江（天然河流）、里运河（人工运河）同级
- 输出结果时需根据 water_classification.md 前置标注

### 高程基准不一致（高频错误）
- 多种基准：废黄河口（里运河）、冻结(吴淞)（长江）
- 跨站对比前必须确认基准相同

### 阈值数据缺失（高频错误）
- **GRZ（保证水位）全表 0% 有值**
- **WRZ（警戒水位）水位站/水文站基本为空**
- 绝对不要硬编码阈值，必须查 st_rvfcch_b 验证

### db 模块路径错误
- ❌ `Path(__file__).parent / 'lib'` 错误
- ✅ `os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib')`

---

## 2. 测站类型编码

| 编码 | 类型 | 对应数据表 |
|------|------|-----------|
| ZZ | 水位站 | st_river_r |
| ZQ | 水文站（水位+流量） | st_river_r |
| RR | 水库站 | st_rsvr_r |
| DD | 闸站 | st_was_r, st_gate_r |
| DP | 泵站 | st_pump_r |
| PP | 雨量站 | st_pptn_r |
| WQ | 水质站 | wq_pcp_d |

---

## 3. 时间范围定义

| 关键词 | 定义 |
|--------|------|
| 实时/最新 | MAX(tm) |
| 某天左右 | 该天的前后3天 |
| 最近 | 当前时间的最近三天 |
| 当前 | 最近10天数据 |
| 最近30天 | `tm >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)` |
| 最近2个月 | `tm >= DATE_SUB(CURDATE(), INTERVAL 2 MONTH)` |

---

## 4. Few-Shot 关键 SQL 模板

### 模板 1：按站名查水位（高频）
```sql
SELECT r.tm AS '时间', r.z AS '水位(m)'
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%{站名}%'
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL {天数} DAY)
  AND r.z IS NOT NULL
ORDER BY r.tm;
```

### 模板 2：年度统计
```sql
SELECT YEAR(tm) AS '年份',
       AVG(z) AS '年平均水位(m)',
       MAX(z) AS '年最高水位(m)',
       MIN(z) AS '年最低水位(m)'
FROM st_river_r
WHERE tm >= '2024-01-01' AND tm < '2025-01-01'
  AND stcd IN ('{stcd1}', '{stcd2}')
GROUP BY YEAR(tm)
ORDER BY YEAR(tm);
```

### 模板 3：跨站对比（含时间窗口）
```sql
SELECT b.stnm AS '测站名称',
       MAX(CASE WHEN r.tm BETWEEN '2024-08-01' AND '2024-08-31' THEN r.z END) AS '8月最高水位(m)',
       MAX(CASE WHEN r.tm BETWEEN '2024-09-01' AND '2024-09-30' THEN r.z END) AS '9月最高水位(m)'
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
  AND r.tm BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY b.stnm;
```

### 模板 4：超警戒判断
```sql
SELECT b.stnm AS '测站名称',
       MAX(r.z) AS '最高水位(m)',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN MAX(r.z) > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
LEFT JOIN st_rvfcch_b rv ON b.stcd = rv.STCD
WHERE b.stnm LIKE '%{站名}%'
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL {天数} DAY)
  AND rv.WRZ IS NOT NULL  -- 阈值存在性检查前置
GROUP BY b.stnm, rv.WRZ;
```

### 模板 5：水位站数量（按河流统计）
```sql
SELECT b.rvnm AS '河流名称', COUNT(b.stcd) AS '水位站数量'
FROM sl323.st_stbprp_b b
WHERE b.sttp = 'ZZ' AND b.rvnm IS NOT NULL AND b.rvnm != ''
GROUP BY b.rvnm
HAVING COUNT(b.stcd) = (SELECT MIN(stcd_count)
                        FROM (SELECT COUNT(stcd) AS stcd_count
                              FROM sl323.st_stbprp_b
                              WHERE sttp = 'ZZ' AND rvnm IS NOT NULL AND rvnm != ''
                              GROUP BY rvnm) AS min_count)
   OR COUNT(b.stcd) = (SELECT MAX(stcd_count)
                       FROM (SELECT COUNT(stcd) AS stcd_count
                             FROM sl323.st_stbprp_b
                             WHERE sttp = 'ZZ' AND rvnm IS NOT NULL AND rvnm != ''
                             GROUP BY rvnm) AS max_count)
ORDER BY COUNT(b.stcd);
```

### 模板 6：实时水位（最新记录）
```sql
SELECT b.stnm AS '测站名称',
       r.z AS '实时水位(m)',
       r.tm AS '更新时间',
       rv.WRZ AS '警戒水位(m)',
       CASE WHEN r.z > rv.WRZ THEN '超警戒' ELSE '正常' END AS '状态'
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
LEFT JOIN st_rvfcch_b rv ON b.stcd = rv.STCD
WHERE b.stnm LIKE '%{站名}%'
  AND r.tm = (SELECT MAX(tm) FROM st_river_r WHERE stcd = b.stcd)
LIMIT 1;
```

---

## 5. 重点河道映射

| 河道名称 | 对应测站 | 备注 |
|---------|---------|------|
| 古运河 | 古运河水位站（新城河口） | — |
| 新城河 | 新城河水文站（兴城西路北） | — |
| 七里河 | 七里河水位站（东花园路） | — |
| 赵家支沟 | 赵家支沟水文站（赵家河路） | — |
| 瘦西湖 | 瘦西湖水位站 | 编码固定为: HT0051003052000022 |

---

## 6. 低分用例分析

### Q2 [water-situation/L1] (0.38 分)
**问题**：查询宝应水位站的所属河流、水系、流域、测站类别。
**根因**：SQL 只查了 st_stbprp_b，但字段选择不完整（未包含 hnnm、bsnm 等）
**S5 改进**：明确 st_stbprp_b 字段含义，提醒"测站属性查询必须 SELECT 所有相关字段"

### Q15 [water-situation/L3] (0.53 分)
**问题**：查询水位站白马闸的实时水位是多少。
**根因**：实时水位 SQL 可能有问题（MAX(tm) 子查询或 LIMIT 1）
**S6 改进**：增加"实时水位查询"标准模板（见模板 6）

### Q19 [water-situation/L3] (0.58 分)
**问题**：查询2025年古运河水位站点的数量。
**根因**：分区裁剪（应使用 `r.tm >= '2025-01-01' AND r.tm < '2026-01-01'`）
**S5 改进**：st_river_r 明确列出"2025 年数据"的正确写法

---

## 7. 水势编码

| 编码 | 含义 |
|------|------|
| 4 | 涨 |
| 5 | 落 |
| 6 | 平 |

---

## 8. 超警戒判断

- `z > WRZ` → 超警戒水位，需启动预警
- `z > GRZ` → 超保证水位/排涝控制水位，需紧急处理

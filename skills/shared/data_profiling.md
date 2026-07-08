<!-- SOURCE: adapted from knowledge-work-plugins/data/skills/explore-data/SKILL.md
     UPSTREAM_LINES: 325 | ADAPTED_LINES: ~240 | MIGRATION: COMPLETE | DATE: 2026-07-08
     注：通用数据画像/质量评估框架已水利化；本次补字符串/日期列画像、外键候选与冗余列探测。 -->
# 数据画像与质量评估

> 遇到新数据集时，在分析前系统理解数据形状、质量和潜力。

## 一、结构理解

### 列分类

| 类别 | 含义 | 水利示例 |
|------|------|---------|
| **标识符** | 唯一键、外键 | stcd, stnm, taskid, uuid |
| **维度** | 分类属性（分组/过滤用） | sttp（ZZ/ZQ/RR/WQ/DD/DP）, area, status, grade |
| **度量** | 定量值 | z（水位）, drp（降雨）, dox（DO）, q（流量） |
| **时间** | 日期/时间戳 | tm, spt, created_at |
| **文本** | 自由文本 | 备注、描述、地名 |
| **布尔** | True/False | is_test, is_employee |

### 粒度理解

- **默认粒度**：`st_river_r` 为每站每次监测值（5min or 自定义间隔）
- **聚合粒度**：根据不同需求按月/日/时汇总
- **主键**：每个表的唯一标识是什么？是否有重复键风险？

---

## 二、画像查询

### 表级概览

```sql
-- 行数 + 时间跨度
SELECT COUNT(*) AS row_count,
       MIN(tm) AS earliest, MAX(tm) AS latest
FROM st_river_r;

-- 测站覆盖
SELECT COUNT(DISTINCT stcd) AS station_count
FROM st_river_r;
```

### 列级画像

```sql
-- 数值列：基础统计
SELECT
    COUNT(*) AS n,
    COUNT(z) AS non_null,
    ROUND(AVG(z), 3) AS mean,
    ROUND(STDDEV(z), 3) AS std,
    ROUND(MIN(z), 3) AS min_val,
    ROUND(MAX(z), 3) AS max_val
FROM st_river_r;

-- 分位计算
-- ① 当前基线（5.7）：无 NTILE 窗口函数，用 pandas（见下方"Python 快速画像脚本"）
--    df['z'].quantile([.01,.05,.25,.5,.75,.9,.95,.99])
-- ② 现代写法（8.0+）：NTILE 窗口函数（分区表务必带 tm 范围，否则全分区扫描超时）
SELECT z, ntile_val FROM (
    SELECT z, NTILE(100) OVER (ORDER BY z) AS ntile_val
    FROM st_river_r WHERE z IS NOT NULL AND tm >= DATE_SUB(NOW(), INTERVAL 7 DAY)
) t WHERE ntile_val IN (1, 5, 25, 50, 75, 95, 99);

-- 维度列：基数 + 频率 Top-10
SELECT sttp, COUNT(*) AS cnt
FROM st_stbprp_b
GROUP BY sttp ORDER BY cnt DESC;

-- 字符串列：长度分布 + 空串 + 大小写/空格一致性（5.7 可跑）
SELECT
    COUNT(*) AS n,
    SUM(stnm IS NULL OR stnm = '') AS empty_cnt,
    MIN(CHAR_LENGTH(stnm)) AS min_len,
    MAX(CHAR_LENGTH(stnm)) AS max_len,
    ROUND(AVG(CHAR_LENGTH(stnm)),1) AS avg_len,
    SUM(stnm = TRIM(stnm)) AS no_padding_cnt,     -- 前后空格探测
    SUM(stnm <> UPPER(stnm) AND stnm <> LOWER(stnm)) AS mixed_case_cnt  -- 大小写混用
FROM st_stbprp_b;

-- 日期/时间列：范围 + 未来值 + 空值（分区表务必带 tm 范围，否则全分区扫描）
SELECT
    COUNT(*) AS n,
    SUM(tm IS NULL) AS null_cnt,
    MIN(tm) AS earliest, MAX(tm) AS latest,
    SUM(tm > NOW()) AS future_cnt                   -- 未来时间 → 时钟不同步
FROM st_river_r
WHERE tm >= DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 布尔/标志列：真值率（水利表常把布尔存为 0/1 或状态码）
SELECT
    COUNT(*) AS n,
    SUM(gtophgt > 0) AS open_cnt,                   -- 例：闸门开启（gtophgt>0 视为开）
    ROUND(AVG(gtophgt > 0) * 100, 1) AS open_rate_pct
FROM st_gate_r
WHERE tm >= DATE_SUB(NOW(), INTERVAL 1 DAY);
```

### Python 快速画像脚本

```python
import pandas as pd
import numpy as np

def profile_table(df: pd.DataFrame, table_name: str = 'table'):
    print(f"=== {table_name} 数据画像 ===")
    print(f"行数: {len(df):,}, 列数: {len(df.columns)}")
    print()

    for col in df.columns:
        null_rate = df[col].isna().mean()
        dtype = df[col].dtype
        n_unique = df[col].nunique()
        print(f"\n--- {col} (dtype={dtype}, null={null_rate:.1%}, unique={n_unique}) ---")

        if pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe(percentiles=[.01, .05, .25, .5, .75, .9, .95, .99])
            print(f"  range: {desc['min']:.3f} - {desc['max']:.3f}")
            print(f"  mean±std: {desc['mean']:.3f} ± {desc['std']:.3f}")
            print(f"  median [p25-p75]: {desc['50%']:.3f} [{desc['25%']:.3f} - {desc['75%']:.3f}]")
            # 分布偏度
            skew = df[col].skew()
            print(f"  skew: {skew:.3f} ({'右偏' if skew > 0.5 else '左偏' if skew < -0.5 else '近似对称'})")

        elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]):
            top10 = df[col].value_counts().head(10)
            print(f"  Top-5:")
            for val, cnt in top10.head(5).items():
                print(f"    [{val}]: {cnt} ({cnt/len(df):.1%})")
```

---

## 三、质量评估框架

### 完整度评分

| 等级 | 非空率 | 含义 |
|------|--------|------|
| 完整 | >99% | 无需处理 |
| 基本完整 | 95-99% | 调查缺失原因 |
| 不完整 | 80-95% | 评估是否可用 |
| 稀疏 | <80% | 可用性低，需插值 |

### 一致性问题

| 问题 | 水利场景 |
|------|---------|
| 值格式不一致 | "扬州" vs "扬州市" vs "YZ" 表示同一地名 |
| 类型不一致 | stcd 在 A 表是 VARCHAR，B 表是 CHAR(8) |
| 引用完整性 | st_river_r.stcd 在 st_stbprp_b 中找不到 |
| 业务规则违反 | 结束时间 < 开始时间；水位变率 > 2m/h |
| 跨列一致性 | 状态=completed 但 completed_at 为空 |

```sql
-- 引用完整性检查
SELECT DISTINCT r.stcd
FROM st_river_r r
LEFT JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stcd IS NULL;
```

### 准确性红旗

| 标志 | 说明 |
|------|------|
| 占位符值 | 0, -1, 9999, "N/A", "未命名" |
| 默认值高频 | 超过 50% 集中在某个值 |
| 无更新 | updated_at 停留在一个月前 |
| 不可能值 | 负降雨量、水位 -5m、DO 25mg/L |
| 整数偏倚 | 所有值以 0 或 5 结尾（估计值而非实测值） |

### 时效性评估

- 表最近更新时间？"数据截至 YYYY-MM-DD HH:mm"
- 预期更新频率？实时 / 逐小时 / 每日
- 事件时间和入库时间的时差？
- 时间序列有无断点？

---

## 四、模式发现

### 分布特征

| 类型 | 特征 | 水利案例 |
|------|------|---------|
| 正态 | 均值≈中位数，钟形 | 长期水位波动（某些站） |
| 右偏 | 长尾在右侧 | 降雨量（多数天无雨，少数天暴雨） |
| 双峰 | 两个峰值 | 潮汐河段水位（高低潮） |
| 幂律 | 少数极大值 | 极端洪水事件频率 |
| 均匀 | 各值频率相近 | 人工设定值、随机采集数据 |

### 时间模式

- **趋势**：持续上升/下降（如多年水位下降）
- **季节性**：年/月/日周期（汛期 vs 非汛期，潮汐）
- **周效应**：工作日 vs 周末（闸门多为工作时间操作）
- **突变点**：趋势转折（如建闸后水位变化）
- **异常点**：孤立偏离值（传感器突跳）

### 分段发现

寻找具有不同行为的自然分组：
- 不同 sttp（水位站 vs 水质站 vs 闸泵站）的指标分布差异
- 山区站 vs 平原站的水位变幅差异
- 骨干河 vs 支流的流量差异

### 相关探索

```sql
-- 水位与流量的相关性（同一站）
SELECT stcd,
       (COUNT(*) * SUM(z*q) - SUM(z)*SUM(q)) /
       SQRT((COUNT(*)*SUM(z*z) - SUM(z)*SUM(z)) * (COUNT(*)*SUM(q*q) - SUM(q)*SUM(q)))
       AS correlation_coefficient
FROM st_river_r
WHERE stcd = '目标站码' AND z IS NOT NULL AND q IS NOT NULL
GROUP BY stcd;
```

> 注意：相关 ≠ 因果。水位和流量同步上升可能是降雨共同驱动。

### 外键候选探测

判断某列是否是指向另一表主键的外键（命中率高 → 大概率是外键）：

```sql
-- st_river_r.stcd 是否指向 st_stbprp_b.stcd
SELECT
    COUNT(*) AS total,
    SUM(b.stcd IS NOT NULL) AS matched,
    ROUND(SUM(b.stcd IS NOT NULL)/COUNT(*)*100, 1) AS match_rate_pct
FROM st_river_r r
LEFT JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE r.tm >= DATE_SUB(NOW(), INTERVAL 7 DAY);
-- match_rate ≈ 100% → 是外键；远低于 → 编码体系不同（见 analysis_validation「测站编码多体系」陷阱）
```

### 冗余列探测

检查两列是否携带重复信息（值分布高度一致 → 可去其一）：

```sql
SELECT
    COUNT(*) AS n,
    SUM(col_a = col_b) AS identical_cnt,            -- 两列逐行相同
    SUM(col_a IS NULL OR col_b IS NULL) AS null_either
FROM 某表
WHERE tm >= DATE_SUB(NOW(), INTERVAL 7 DAY);
-- identical_cnt/n 接近 1 且 null 少 → 两列冗余
```

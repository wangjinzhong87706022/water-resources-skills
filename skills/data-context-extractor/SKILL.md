---
name: data-context-extractor
description: "数据上下文提取 — 探索新数据源时系统化提取元数据、分布特征、质量指标。为后续分析提供基线上下文。适合首次接入新表/新库、或者排查数据质量问题时使用。"
version: 1.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, data-profiling, metadata, discovery, schema]
    category: water-resources
    related_skills: [water-situation, rainfall, water-quality, water-fusion]
---

# 数据上下文提取 (Data Context Extractor)

探索新数据源时系统化提取元数据、分布特征、质量指标。为后续分析提供基线上下文。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 首次接入一个新表/新库 | Yes |
| 排查数据质量问题（NULL、异常值、格式不一致） | Yes |
| 需要了解某表有哪些列、什么类型、覆盖什么时间范围 | Yes |
| 日常查询已知表 | **No，用对应数据 skill** |

## Prerequisites

- **数据库访问权限:** 可执行 SQL（只读）
- **pymysql:** 如未安装需先 `pip install pymysql`
- **参考:** `shared/data_profiling.md` — 数据画像方法论的完整参考
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则
- 参考 `shared/statistical_methods.md` — 统计方法（分布特征描述）

## Workflow

1. **探索元数据。**
   ```sql
   -- 表结构
   DESC table_name;
   -- 行数估计
   SELECT COUNT(*) FROM table_name;
   -- 时间范围（如有时间列）
   SELECT MIN(tm), MAX(tm) FROM table_name;
   -- NULL 率（每列）
   SELECT
     SUM(IF(col1 IS NULL, 1, 0)) / COUNT(*) AS col1_null_rate,
     SUM(IF(col2 IS NULL, 1, 0)) / COUNT(*) AS col2_null_rate
   FROM table_name;
   ```
2. **数值列分布。** 对于每列数值型列，提取 min/p25/p50/p75/max/avg/stddev。
3. **类别列枚举。** 对于每列字符型列，提取唯一值数和 Top 5。检查是否有编码规范（如 sttp 的 ZZ/ZQ/RR）。
4. **时间序列特征。** 如有时序数据，检查采样间隔是否均匀、是否有缺失日期段、最新数据时间。
5. **质量标记。** 对所有发现的质量问题打标记：
   - NULL 率 > 10% → ⚠️ 高缺失率
   - 数值列 stddev=0 → ⚠️ 全常数值，可能未更新
   - 最新数据距今 > 30 天 → ⚠️ 数据陈旧
   - 唯一值数 > 预期 10 倍 → ⚠️ 可能有脏数据
6. **输出上下文摘要。** 格式化为 Markdown，包括：
   - 表概要（库、行数、时间范围）
   - 列字典（名称、类型、NULL 率、示例值）
   - 质量标记列表
   - 建议（使用前需注意的问题）

## Column Classification

| 类型 | 判断依据 | 处理方法 |
|------|---------|---------|
| 时间 | 含 date/time/timestamp | 提取范围、间隔、缺失段 |
| 数值 | int/decimal/float | 分布统计 + 异常值检测 |
| 类别 | varchar 且唯一值 < 20 | 枚举值列表 + 频率分布 |
| 标识 | varchar 且唯一值 ≈ 行数 (stcd/stnm) | 唯一性确认 + 样例 |
| 文本 | 长 varchar/text 且唯一值多 | 长度分布 + 常见前缀 |
| 标记 | tinyint/int 且取值 0/1 | 比率 + 缺失检查 |

## Output Format

```markdown
## 数据上下文: [库名].[表名]

**概要:** 12 列 × 45,832 行 · 时间范围: 2024-01-01 ~ 2026-06-30

**列字典:**
| 列名 | 类型 | NULL 率 | 示例 | 备注 |
|------|------|---------|------|------|
| stcd | varchar(8) | 0% | "321200" | 测站编码，唯一 |
| tm | datetime | 0% | 2026-06-30 08:00 | 主键之一 |
| z | decimal(5,2) | 2.1% | 3.45 | 水位，单位 m |

**质量标记:**
- ⚠️ z 列 2.1% NULL（夜间缺报）
- ⚠️ 最新数据：2026-06-30（实时）

**建议:** 该表结构规整，水位列有少量 NULL 可忽略。
```

## Related Skills

- `data_profiling.md` — 本 skill 使用的方法论参考
- `water-situation` / `rainfall` / `water-quality` — 数据源
- `water-fusion` — 融合查询前对数据源进行画像

---
name: water-fusion
description: "水利跨域智能融合查询 — 编排多个水利 skill 的协同查询、数据关联、智能融合和冲突消解。基于专利方案的三维关联（时间/空间/业务）+ 融合图 + 对齐策略。"
version: 1.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, fusion, cross-domain, orchestration, correlation]
    category: water-resources
---

# 水利跨域智能融合查询 (Water Fusion)

编排多个水利 skill 的协同查询，通过三维关联（时间/空间/业务）实现数据智能融合。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 查询涉及 2+ 个业务域（水位+降雨、水质+预警等） | Yes |
| 需要"综合分析"、"对比"、"影响分析" | Yes |
| 单一业务域查询 | **No，用对应 skill** |

## Prerequisites

- **DB 助手模块:** `from db import query`（见 shared/db_connection.md）
- **执行策略模块:** `from planner import plan_execution`（见 lib/planner.py）
- **融合模块:** `from fusion import correlate, fuse, detect_conflicts, resolve_conflicts`（见 lib/fusion.py）
- 参考 `references/business_rules.md` — 业务关联规则和依赖关系
- 参考 `shared/sql_safety_rules.md` — SQL 安全规则
- 参考 `shared/analysis_validation.md` — 分析验证（融合输出的置信度评定和陷阱检查）
- 参考 `shared/sql_patterns.md` — SQL 通用查询模式（跨表 JOIN、窗口函数对齐）

## Workflow

1. **识别涉及 Skill。** 根据用户问题判断涉及哪些业务域。参考下方关键词映射。
2. **规划执行策略。** 调用 `plan_execution(skills)` 获取串行/并行执行计划。
   ```python
   import sys
   sys.path.insert(0, str(Path(__file__).parent / 'lib'))
   from planner import plan_execution
   plan = plan_execution(["rainfall", "water-situation", "water-warning"])
   # plan["steps"] = [["rainfall", "water-situation"], ["water-warning"]]
   ```
3. **执行查询。** 按执行计划调用各 skill 的 db.py 获取数据。同一并行组内的查询可依次快速执行。
   ```python
   from db import query
   rainfall_rows = query("SELECT ...", db='sl323')
   water_rows = query("SELECT ...", db='sl323')
   warning_rows = query("SELECT ...", db='sl323')
   ```
4. **关联分析。** 调用 `correlate()` 识别三维关联。
   ```python
   from fusion import correlate, fuse
   correlations = correlate({"rainfall": rainfall_rows, "water-situation": water_rows})
   # 返回: {"time": [...], "spatial": [...], "business": [...]}
   ```
5. **智能融合。** 调用 `fuse()` 执行时间/空间/业务对齐合并。
   ```python
   fused = fuse({"rainfall": rainfall_rows, "water-situation": water_rows}, correlations)
   # fused["strategy_used"] = "time" | "spatial" | "business"
   # fused["data"] = 合并后的数据列表
   ```
6. **冲突消解。** 如有冲突，检测并消解。
   ```python
   from fusion import detect_conflicts, resolve_conflicts
   conflicts = detect_conflicts(fused["data"])
   resolved, log = resolve_conflicts(fused["data"], conflicts, strategy="latest")
   ```
7. **输出综合报告。** 格式化融合结果，必须包含以下全部段落：
   - **数据摘要**: 各 skill 的查询结果摘要
   - **融合分析**: 用"关联""影响""对比""综合分析""因果"等词汇描述跨域数据关系（如"降雨对水位的影响""水位与预警的关联"）
   - **融合策略**: 说明使用的时间对齐/空间对齐/业务逻辑策略
   - **综合数据表格**: 融合后的数据（表格形式）
   - **结论**: 一句话总结跨域查询的综合结论
8. **输出验证。** 交付前按 shared/analysis_validation.md 做置信度评定。

## Validation Gate

**每个融合查询交付前必须通过以下验证。** 未通过项标注在报告末尾。

### 行数合理性检查

```python
# 预期范围: 输入 skill 数量 × 时间窗口天数 × 站数 × 0.5~2
n_input = len([rainfall_rows, water_rows, warning_rows])  # 输入 skill 数
days = (tm_max - tm_min).days if 'tm_max' in dir() else 30
stations = len(set(r['stcd'] for r in water_rows))
expected_min = n_input * min(days, 90)  # 上限 ~90 天
if len(fused["data"]) > expected_min * 10:
    mark("WARN: 融合后行数异常膨胀 ({}行 > {}行预期)".format(len(fused["data"]), expected_min * 10))
if len(fused["data"]) < max(1, n_input):
    mark("WARN: 融合后行数过少 ({}行)，可能 JOIN 丢失数据".format(len(fused["data"])))
```

### 数值合理性检查

| 指标 | 合理范围 | 常见问题 |
|------|---------|---------|
| 水位 z | -1 ~ 20m | 跨表对齐时错位到异常值 |
| 降雨 drp | 0 ~ 600mm/d | 融合后的均值被暴雨极值拉偏 |
| CODMn | 0 ~ 50mg/L | 多站平均时被污染站拉高 |
| DO | 0 ~ 20mg/L | 时间对齐后取值错位 |

### 检查清单（6 项）

- [ ] **行数检查**: 融合结果未异常膨胀或过少
- [ ] **数值范围**: 所有数值落在业务合理区间
- [ ] **时间对齐**: 跨 skill 数据使用相同时间粒度（日/时/月）
- [ ] **站名一致性**: 相同测站在所有 skill 中使用同一名称
- [ ] **均值检查**: 融合后的均值未被极端值拉偏（与中位数对比）
- [ ] **空值检查**: 融合结果没有因 JOIN 注入意外 NULL

### 置信度评定

通过 6 项检查 → **高置信度**；1-2 项未通过 → **有保留**（报告中标注具体问题）；3+ 项未通过 → **需修订**（返回步骤 4 重新融合）。



## Skill 关键词映射

| 关键词 | Skill |
|--------|-------|
| 水位/水情/水文/河流/实时水位 | water-situation |
| 降雨/雨量/降水/暴雨 | rainfall |
| 水质/溶解氧/氨氮/CODMn/总磷/评级/等级 | water-quality |
| 预测/预报/未来水位/模型 | water-forecast |
| 闸/泵/开度/流量/启闭 | gate-pump-operation |
| 预警/超警戒/超保证/防洪/警戒水位/判断等级 | water-warning |

## 融合策略选择

| 场景 | 策略 | 说明 |
|------|------|------|
| 不同 skill 数据有相同时间范围 | 时间对齐 | 按时间粒度合并同时间点数据 |
| 不同 skill 涉及相同测站 | 空间对齐 | 按站名归一化后合并 |
| 有业务因果规则匹配 | 业务逻辑 | 分析因果关联（如降雨→水位） |
| 多维度同时存在 | 自动选择 | 选最强关联维度作为主策略 |

## Related Skills

- `water-situation` — 水位查询
- `rainfall` — 降雨查询
- `water-quality` — 水质查询
- `water-forecast` — 水位预测
- `gate-pump-operation` — 闸泵工况
- `water-warning` — 水利预警
- `water-visualization` — 水利可视化

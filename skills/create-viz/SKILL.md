---
name: create-viz
description: "可视化报告生成 — 从数据到最终交付物的完整工作流。自动完成数据获取→分析→图表→排版→导出。适合需要完整可视化交付物的场景（日报、周报、专题报告）。"
version: 1.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, visualization, report, presentation, export]
    category: water-resources
    related_skills: [water-visualization, build-dashboard, water-situation, rainfall, water-quality, water-forecast, gate-pump-operation, water-warning]
---

# 可视化报告生成 (Create Viz)

从数据到最终交付物的完整工作流。自动完成数据获取→分析→图表→排版→导出。适合日报/周报/专题报告场景。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 需要一份完整的水利可视化报告（含数据+图表+结论） | Yes |
| 日报/周报自动生成 | Yes |
| 专题分析报告（汛期总结、年度水质分析等） | Yes |
| 只需要单张图表 | **No，用 water-visualization** |

## Prerequisites

- **数据来源:** 依赖数据 skill 先获取数据，或上下文中已有查询结果
- **图表能力:** 依赖 water-visualization 生成子图表
- **排版输出:** Python + matplotlib/plotly + reportlab（PDF，可选）
- 参考 `shared/statistical_methods.md` — 报告中的统计分析和异常检测
- 参考 `shared/analysis_validation.md` — 报告结论的置信度评定和陷阱检查

## Workflow

1. **确定报告类型与受众。**
   - 日报：简洁为主，关键指标+1~2 张趋势图
   - 周报：趋势+对比+排名，3~5 张图
   - 专题报告：问题→分析→结论→建议完整结构
2. **数据获取与预处理。** 调用对应数据 skill，按 shared/statistical_methods.md 做描述统计和异常标记。
3. **分析。** 识别关键发现（最高/最低/突变/超阈值），计算趋势和对比指标。
4. **生成图表。** 对每个关键发现生成对应图表。优先 plotly 交互式，备选 matplotlib 静态。
5. **排版。** 按报告类型组织内容结构：
   - **日报**: 标题区块 → KPI 行 → 趋势图 → 数据表
   - **周报**: 摘要 → 逐日趋势 → 同比/环比 → 排名 → 表格
   - **专题**: 背景 → 数据 → 分析 → 发现 → 建议
6. **添加上下文。** 每张图表附关键结论文字——不要只放图，要解释"图告诉我们什么"。
7. **导出。** 报告保存为 HTML（推荐，保留交互性）或 PDF（正式汇报）。

## Report Templates

### 日报模板
```
[标题] XXXX 水位日报 YYYY-MM-DD
[KPI 行] 当前水位 | 日涨幅 | 距警戒 | 昨日最大 | 最小
[趋势图] 近 30 天水水位折线（含警戒线）
[数据表] 各站最高/最低/平均水位
[结论] 一句话总结当日情况
```

### 周报模板
```
[标题] XXXX 第 WW 周水利简报
[摘要] 本周核心结论（3 点以内）
[趋势] 水位/降雨/水质趋势图
[对比] 本周 vs 上周同比/环比
[排名] 变化最大的前 5 站
[表格] 各站汇总数据
[附录] 异常事件记录
```

### 专题报告模板
```
[封面] 标题/日期/作者
[背景] 问题描述和分析目的
[数据] 数据来源和时间范围
[分析] 核心分析内容和图表
[发现] 关键发现列表
[建议] 基于数据的行动建议
```

## Related Skills

- `water-visualization` — 单图表生成
- `build-dashboard` — 监控看板（日报的另一种形态）
- `data-context-extractor` — 新数据源接入时的数据画像
- 各数据 skill — 数据来源

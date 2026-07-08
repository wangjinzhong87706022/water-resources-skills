---
name: build-dashboard
description: "水利仪表盘构建 — 将多个图表和数据源组合为统一看板。支持网格布局、交互联动、自动刷新、导出分享。与 water-visualization 配合使用。"
version: 1.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, dashboard, visualization, monitoring, realtime]
    category: water-resources
    related_skills: [water-visualization, water-situation, rainfall, water-quality, water-warning]
---

# 水利仪表盘构建 (Build Dashboard)

将多个水利图表和数据卡片组合为统一看板，支持监控视图、管理视图、综合报告等多种形态。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 需要组合 3+ 个图表到一个页面 | Yes |
| 需要水位+降雨+水质综合监控面板 | Yes |
| 需要导出为固定布局报告 | Yes |
| 只需要单个图表 | **No，用 water-visualization** |

## Prerequisites

- **数据来源:** 先调用对应数据 skill 获取数据
- **图表生成:** 先调用 water-visualization 生成各子图表
- 参考 `shared/data_profiling.md` — 数据画像（接入新数据源时评估数据质量）
- 参考 `shared/analysis_validation.md` — 分析验证（仪表盘结论的置信度评定）

## Workflow

1. **明确看板用途。** 监控（实时刷新）、管理（日报/周报）、还是综合报告（一次性）。
2. **确定布局结构。**
   - 监控面板：顶部 KPI 卡片行（4~6 个关键指标）+ 下方图表网格
   - 日报面板：左趋势右对比，按业务域分区
   - 综合报告：阶梯式布局，关键结论→支撑图表→详细数据
3. **生成各子图表。** 调用 water-visualization 按单个图表模板生成，记录每个图表的文件路径。
4. **组合布局。** 按确定的结构拼接——优先使用 plotly subplots 或 HTML div 网格，matplotlib subplots 作为备选。
5. **添加联动（可选）。** plotly 图表间共享 hover 事件实现交叉筛选。
6. **导出。** HTML（交互式）、PNG（静态报告）、PDF（打印）。

## Layout Patterns

| 模式 | 适用场景 | 布局 |
|------|---------|------|
| KPI + 网格 | 实时监控 | 顶部 4~6 KPI 卡片 + 2×2 或 3×3 图表网格 |
| 左右对比 | 双域分析 | 左水位 + 右降雨 / 左预测 + 右实测 |
| 阶梯式 | 综合报告 | 结论行 → 趋势图 → 明细表 → 附录 |
| Tab 式 | 多域管理 | 每 Tab 一个业务域（水位/水质/闸泵） |

## Related Skills

- `water-visualization` — 单图表生成（本 skill 依赖）
- `data-context-extractor` — 数据源画像（新看板接入时评估）
- `water-situation` / `rainfall` / `water-quality` / `water-warning` — 数据源

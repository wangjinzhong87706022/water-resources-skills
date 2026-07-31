---
name: build-dashboard
description: "水利仪表盘构建 — 将多个图表和数据源组合为统一看板。支持网格布局、KPI 卡片、静态 PNG 快照交付。与 water-visualization 配合使用。"
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
- **图表生成:** 先调用 water-visualization 生成各子图表（沙箱三铁律：禁 pip install；脚本 write_file 落盘再 bash 执行，禁 heredoc；CJK 字体 `['Noto Sans CJK SC','WenQuanYi Micro Hei','DejaVu Sans']`）
- **交付形态:** 看板 = matplotlib subplots 拼合的 PNG（绝对路径 `/mnt/user-data/outputs/xxx.png` 内嵌回复正文）。**沙箱无法交付实时刷新、交互联动、plotly HTML**——不要承诺
- 参考 `shared/data_profiling.md` — 数据画像（接入新数据源时评估数据质量）
- 参考 `shared/analysis_validation.md` — 分析验证（仪表盘结论的置信度评定）

## Workflow

1. **明确看板用途。** 监控快照（一次性）、管理（日报/周报）、还是综合报告。**注：沙箱产出均为静态 PNG 快照，无自动刷新。**
2. **确定布局结构。**
   - 监控面板：顶部 KPI 卡片行（4~6 个关键指标）+ 下方图表网格
   - 日报面板：左趋势右对比，按业务域分区
   - 综合报告：阶梯式布局，关键结论→支撑图表→详细数据
3. **生成各子图表。** 调用 water-visualization 按单个图表模板生成，记录每个图表的文件路径。
4. **组合布局。** 用 matplotlib `plt.subplots()` / `GridSpec` 拼接为单张 PNG；KPI 卡片用 `ax.text()` 大字号实现。
5. **交付。** 看板 PNG 内嵌对话回复正文 `![看板](/mnt/user-data/outputs/xxx.png)`，附各分区关键结论文字。

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

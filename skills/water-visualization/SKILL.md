---
name: water-visualization
description: "水利数据可视化 — 水位趋势图、降雨量分布图、水质变化图、闸泵运行状态图。与 water-situation/rainfall/water-quality/gate-pump-operation 配合使用。"
version: 1.0.0
author: dataagent-water-resources
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [water, visualization, chart, matplotlib, plotly, dashboard, plotting]
    category: water-resources
    related_skills: [water-situation, rainfall, water-quality, water-forecast, gate-pump-operation, water-warning]
---

# 水利数据可视化 (Water Visualization)

将水利查询结果（水位、降雨、水质、闸泵）转化为专业图表。可独立使用，也可与任意水利数据 skill 组合。

## When to Use

| Scenario | Use This Skill |
|----------|---------------|
| 用户要求画图/图表/可视化/趋势图 | Yes |
| 需要展示水位随时间变化趋势 | Yes |
| 需要对比降雨量/水位/水质数据 | Yes |
| 需要展示闸泵运行状态仪表盘 | Yes |
| 纯数据查询（不要图） | No |

## Prerequisites

- **Python 包:** matplotlib, pandas（如未安装需先 `pip install matplotlib pandas`）
- **CJK 字体:** 中文字符必须设置 CJK 字体，否则显示为方块
- **数据来源:** 上下文中已有的查询结果，或先调用对应数据 skill 获取数据
- 参考 `references/chart_templates.md` — 各类水利图表的代码模板

## CJK 字体设置（必须）

matplotlib 默认不支持中文。**所有图表都必须设置 CJK 字体**：

```python
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
```

若 rcParams 不生效，使用 FontProperties：
```python
import matplotlib.font_manager as fm
font_prop = fm.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.title('标题', fontproperties=font_prop)
```

## Workflow

1. **确认数据来源。** 检查上下文中是否有查询结果。如果没有，提示用户先查询数据（或调用对应 skill）。
2. **选择图表类型。** 根据数据特征和用户意图选择：
   - 水位/流量随时间变化 → 折线图（多站可叠加）
   - 降雨量对比 → 柱状图
   - 水质等级分布 → 堆叠柱状图或阶梯图
   - 闸泵运行状态 → 仪表盘/状态面板
   - 多站水位对比 → 多子图或分组折线
3. **生成代码。** 参照 `references/chart_templates.md` 中的模板，替换数据和参数。
4. **执行代码。** 使用 execute_code 工具执行 Python 代码生成图表文件。
5. **返回结果。** 展示图表文件路径 + 关键发现简述。

## Chart Type Selection Guide

| 数据类型 | 图表类型 | 适用 Skill |
|---------|---------|-----------|
| 水位随时间变化 | 折线图 | water-situation, water-forecast |
| 多站水位对比 | 多子图/分组折线 | water-situation |
| 降雨量按时间/区域 | 柱状图 | rainfall |
| 累计降雨量对比 | 堆叠柱状图 | rainfall |
| 水质等级变化 | 阶梯图/堆叠柱状图 | water-quality |
| 水质指标雷达图 | 雷达图 | water-quality |
| 预测 vs 实际水位 | 双线折线图（含置信区间） | water-forecast |
| 闸门开度/泵站流量 | 仪表盘/柱状图 | gate-pump-operation |
| 预警状态汇总 | 状态面板/KPI卡片 | water-warning |

## Supported Technologies

- **matplotlib** — 基础绑图库，适合静态图表
- **pandas** — 数据处理（DataFrame 直接 plot）
- **seaborn** — 统计可视化（可选，需 `pip install seaborn`）

## Best Practices

- 所有图表标题、轴标签使用中文，必须设置 CJK 字体
- 图表宽度建议 12-14 英寸，高度 6-8 英寸（figsize=(14,7)）
- 导出 DPI 150+，文件保存为 PNG
- 多站数据用不同颜色区分，添加图例
- 时间轴 x 轴标签旋转 45 度防止重叠
- 水位值保留 2 位小数

## Related Skills

- `water-situation` — 水位数据源
- `rainfall` — 降雨数据源
- `water-quality` — 水质数据源
- `water-forecast` — 预测数据源
- `gate-pump-operation` — 闸泵数据源
- `water-warning` — 预警数据源

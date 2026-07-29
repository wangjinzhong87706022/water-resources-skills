---
name: water-visualization
description: "水利数据可视化 — 水位趋势图、降雨量分布图、水质变化图、闸泵运行状态图。与 water-situation/rainfall/water-quality/gate-pump-operation 配合使用。"
version: 2.0.0
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

- **Python 包:** matplotlib、pandas、numpy 沙箱已预装，直接 import。**🚫 禁止 `pip install` / `python -m venv`**——沙箱系统 Python 会拒绝（externally-managed / No module named pip），反复重试会烧掉多个轮次直至 recursion limit（实测 Q14/Q23 因此失败）。plotly/seaborn 未必可用，缺则改用 matplotlib，不要尝试安装。
- **CJK 字体:** 中文字符必须设置 CJK 字体，否则显示为方块
- **数据来源:** 上下文中已有的查询结果，或先调用对应数据 skill 获取数据
- 参考 `references/chart_templates.md` — 各类水利图表的代码模板

## CJK 字体设置（必须）

matplotlib 默认不支持中文。**所有图表都必须设置 CJK 字体**：

```python
import matplotlib
# 宿主机实测只装了 Noto Sans CJK SC（未装 WenQuanYi/SimHei）；勿改、勿找字体
matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
```

若 rcParams 不生效，使用 FontProperties：
```python
import matplotlib.font_manager as fm
font_prop = fm.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.title('标题', fontproperties=font_prop)
```

## Workflow

### 🔴 先读这三条铁律，再走下面的步骤

1. **每步必须产出实质性交付物。** 一个完整的 LLM 调用必须完成一项可交付的工作——查数据并落 CSV / 生成一张图表 / 写出最终报告的正文与嵌图。**禁止**输出短于 100 token 的中间回复（如"正在思考""还需查询""让我确认一下"），那会让 agent 循环空转、白白浪费多次往返。如果当前步骤产出 <100 token，说明不该单独成一步，应合并到上一步里。

2. **完整报告 + 所有图直接写在「对话回复正文」里，不另存 .md 报告文件。** 对话回复就是交付物（标题/结论/图/表/发现全部写在这里）。**严禁** `open(...).write(...)` 把报告另存成 `.md` 文件再让用户去翻——实测：落盘 → 前端只剩摘要、图显示成文字。落盘文件只保留两类：数据 CSV（查画解耦）和图表 PNG。报告文字不落盘。

3. **脚本必须 write_file 落盘再 bash 执行，禁止 heredoc 内联。** 不要写 `python << 'EOF' ... EOF`——沙箱路径守卫会把代码里的 `width/2.,`、`x/2` 等片段误判成绝对路径而拒绝执行（`Unsafe absolute paths in command: /2.,`）。正确做法：`write_file` 写到 `/mnt/user-data/workspace/plot.py`，再 `bash: python3 /mnt/user-data/workspace/plot.py`。（实测 Q13 因此连烧 2 轮触顶失败。）

### 具体步骤

1. **理解数据与分析目标。** 先确认数据结构（维度、数值、时间列）和用户意图——趋势、对比、分布还是异常检测？问题决定图表类型。
2. **准备数据（查画解耦，强制）。** 在**数据脚本**里聚合/透视/重采样，得到干净的 DataFrame 后**落盘成 CSV**：`df.to_csv('/mnt/user-data/workspace/plot_data.csv', index=False)`。绘图脚本只读这个 CSV。**严禁在绘图脚本里 `query()` 或连数据库**——查画耦合是画图反复失败、反复重写的头号原因（每次重写 ~2000 token decode，本地 27B 约 60~80s/次）。
3. **选择图表类型。** 根据数据特征和用户意图选择（见下方 Chart Type Selection Guide）。
   - 水位/流量随时间变化 → 折线图（多站可叠加）
   - 降雨量对比 → 柱状图
   - 水质等级分布 → 堆叠柱状图或阶梯图
   - 闸泵运行状态 → 仪表盘/状态面板
   - 多站水位对比 → 多子图或分组折线
4. **生成代码（照抄黄金模板）。** 先读 `references/chart_templates.md` 的「**0. 一次成功铁律**」和「黄金模板」，**照抄、只改 4 处**（CSV 路径 / x 列 / y 列 / 标题）。不要从零写脚本、不要自造多子图布局。绘图前 `df.dropna(subset=[绘图列])` 先洗后画。优先 plotly 做交互图，matplotlib 做静态报告图。
5. **执行代码。** 使用 execute_code 工具执行 Python 代码生成图表文件。
6. **添加上下文注解。** 在图表上用标注、参考线、阴影区突出关键数据点（如警戒水位线、超阈值区域）。
7. **返回结果：完整报告 + 图都写在「对话回复正文」里，不要另存 .md 报告文件。**
   - **对话回复就是交付物**：标题、结论、**图片**、数据表、关键发现，**全部直接写在回复正文**。**严禁**把报告 `open(...).write(...)` 成单独的 `.md` 文件再让用户去翻——那样前端对话区会变得单薄，且文件里的图渲染不出来（实测过：报告落盘 → 前端只剩摘要 + 图显示成 alt 文本）。
   - **图必须内嵌在回复正文**，且路径**必须用绝对路径** `/mnt/user-data/outputs/<文件名>.png`。DeerFlow 只解析这种绝对路径形式；**相对路径**（如 `古运河水位对比.png`）或只写进文件里的路径**都渲染不出**，会显示成文字。格式照抄：
     ```markdown
     ![古运河水位对比](/mnt/user-data/outputs/古运河水位对比.png)
     ```
   - **生成多张图时，每张都必须在回复正文内嵌一个 `![标题](/mnt/user-data/outputs/xxx.png)`（生成 N 张 → 嵌 N 张）**。漏嵌的图用户在前端看不到（实测：生成 2 张只嵌 1 张 → 前端只渲染 1 张，另一张白生成）。
   - 回复结构：`## 标题` → 一句话结论 → **`![图](/mnt/user-data/outputs/xxx.png)`**（放结论后最显眼处）→ 数据表 → 关键发现 → 局限性说明。
   - **落盘文件只保留两类**：数据 CSV（查画解耦用）和图表 PNG。**报告文字不落盘**，直接写在回复里。

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

- **matplotlib** — 基础绑图库，适合静态报告图表
- **pandas** — 数据处理（DataFrame 直接 plot）
- **plotly / plotly.express** — 交互式图表（悬停显示数值、缩放、平移、双轴对比），保存为 HTML 可嵌入报告
- **seaborn** — 统计可视化（可选），适合密度图、箱线图、热力图；未预装则改用 matplotlib 实现，**不要 pip install**

## Best Practices

### Design Principles

- **问题驱动选图。** 根据分析目标选择图表类型，而非数据形态。趋势→折线；对比→柱状；分布→直方图/箱线图；关系→散点图；相关性→热力图。
- **一图一焦点。** 每个图表回答一个问题。避免在一个图中塞入过多信息。
- **数据-墨水比最大化。** 去除不必要的网格线、边框、阴影。保持简约。

### Visual Configuration

- 所有图表标题、轴标签使用中文，必须设置 CJK 字体
- 图表宽度建议 12-14 英寸，高度 6-8 英寸（figsize=(14,7)）
- 导出 DPI 150+，文件保存为 PNG；plotly 同时保存 HTML
- 多站数据用不同颜色区分，添加图例；颜色至少间隔4色以区分
- 时间轴 x 轴标签旋转 45 度防止重叠
- 水位值保留 2 位小数
- 默认使用色盲友好配色（viridis/cividis 色板），颜色类别不超过 7 种
- 柱状图 y 轴从 0 开始，避免夸大差异
- 标注单位：水位(m)、流量(m³/s)、降雨(mm)、浓度(mg/L)

### Annotations & Context

- 水位图中用红色虚线标记警戒/保证水位线，用 `ax.axhline(y=WRZ, color='red', linestyle='--')`
- 超标区域用 `ax.fill_between()` 浅红色阴影标注
- 标注关键极值点：`ax.annotate(f'最高 {max_z:.2f}m', xy=(date, max_z))`
- 预测 vs 实测对比图加置信区间带状区域

## Edge Cases

- **类别过多。** 显示 Top N，其余归入"其他"，或改用树图。
- **数据点重叠。** 折线图用透明度(`alpha=0.7`)，散点图加抖动(jitter)或六边形分箱(hexbin)。
- **长轴标签。** 旋转 45 度或改用水平柱状图。
- **缺失值。** 折线图的小缺口线性插值；大缺口断开线条并标注数据缺失。
- **严重偏斜数据。** 应用对数坐标，在轴标签中注明"log 尺度"。
- **时间序列不等间隔。** 先用 pandas resample 对齐到固定频率（日/时），再绘图。

## Related Skills

- `water-situation` — 水位数据源
- `rainfall` — 降雨数据源
- `water-quality` — 水质数据源
- `water-forecast` — 预测数据源
- `gate-pump-operation` — 闸泵数据源
- `water-warning` — 预警数据源

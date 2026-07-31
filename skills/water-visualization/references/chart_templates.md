# 水利图表模板

> 各类水利场景的 matplotlib 代码模板。替换数据和参数即可使用。

## 公共头部（所有模板必须包含）

```python
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

# CJK 字体（按宿主机实测安装情况排序：Noto 已装、WenQuanYi 备选；切勿改成未安装的字体）
matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# 输出目录（DeerFlow sandbox 可写路径；绘图前必须保证存在）
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
```

> **字体说明（重要）**：宿主机实测只装了 `Noto Sans CJK SC`，**未装** `WenQuanYi Micro Hei` / `SimHei`。上面的列表把已装的 Noto 放第一位，不要改、不要花时间找字体。乱码只因用错字体名。

---

## 0. 一次成功铁律（先读这条，再选下面的具体模板）

实测一次"画图"失败会触发 LLM 重写整段代码 2~3 次，每次重写都是 ~2000 token 的 decode（本地 27B 约 60~80s/次），是耗时大头。下列铁律把"画图"从「从零写脚本」变成「照抄模板填参数」，争取一次成功：

1. **查画解耦（最关键）。** 数据步骤查一次 SQL，**落盘成 CSV**；绘图步骤**只读 CSV**，绘图脚本里**严禁出现 `query()` / 连数据库**。
   ```python
   # 数据步骤末尾（在查询脚本里）：
   df.to_csv('/mnt/user-data/workspace/plot_data.csv', index=False)
   # 绘图步骤开头（在画图脚本里）：
   df = pd.read_csv('/mnt/user-data/workspace/plot_data.csv')
   ```
2. **照抄「黄金模板」，只改 4 处**：`CSV_PATH`、x 列、y 列、标题。不要重写结构、不要自造子图布局、不要堆装饰性 `print`/注释。
3. **先洗后画。** 绘图前 `df = df.dropna(subset=[<绘图列>])`，避免 None 喂进 matplotlib 报错。
4. **单图单脚本。** 需要多张图就多跑几次模板，别在一个脚本里 `delaxes`/`reshape` 玩多子图布局（最容易出错）。多子图仅限照抄模板 5/7，不要自造布局。
5. **路径用 `OUT_DIR`**（已在公共头部定义），不要写裸文件名 `savefig('x.png')`。

### 黄金模板（完整可运行，照抄即用）

```python
import os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)

# ---- 只改这 4 处 ----
CSV_PATH = '/mnt/user-data/workspace/plot_data.csv'
X_COL, Y_COL, GROUP_COL = 'mo', 'avg_z', 'yr'
TITLE = '古运河月度平均水位对比'
OUT_NAME = 'water_compare.png'
# --------------------

df = pd.read_csv(CSV_PATH)
df = df.dropna(subset=[Y_COL])                 # 先洗：丢掉空值，防 None 报错

fig, ax = plt.subplots(figsize=(14, 6))
for key, g in df.groupby(GROUP_COL):
    g = g.sort_values(X_COL)
    ax.plot(g[X_COL], g[Y_COL], marker='o', label=f'{key}')

ax.set_title(TITLE, fontsize=16)
ax.set_xlabel(X_COL); ax.set_ylabel('平均水位 (m)')
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()

out = os.path.join(OUT_DIR, OUT_NAME)
plt.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print(f'图表已保存: {out}')
```

---

> **⚠️ 模板 1-9 使用前必读**：以下每个模板都假定已包含「公共头部」（含 `import os` 与 `OUT_DIR` 定义）。使用前必须：① 读 CSV 后对时间列执行 `pd.to_datetime`（`pd.read_csv` 读入的时间列是字符串，直接喂 mdates 会报错）；② 绘图前 `df = df.dropna(subset=[<关键数值列>])`（与黄金模板做法一致，防 None 喂进 matplotlib）；③ `savefig` 一律用 `OUT_DIR` 绝对路径（前端只渲染 `/mnt/user-data/outputs/` 下的 PNG，裸文件名不渲染）。

## 1. 水位趋势折线图

适用：water-situation, water-forecast — 单站或多站水位随时间变化。

```python
df['tm'] = pd.to_datetime(df['tm'])   # CSV 读入的 tm 是字符串，必须先转
df = df.dropna(subset=['z'])          # 先洗后画

fig, ax = plt.subplots(figsize=(14, 6))

for stnm, group in df.groupby('stnm'):
    ax.plot(group['tm'], group['z'], marker='o', markersize=3, label=stnm)

ax.set_title('水位变化趋势', fontsize=16)
ax.set_xlabel('时间', fontsize=12)
ax.set_ylabel('水位 (m)', fontsize=12)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
plt.xticks(rotation=45)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'water_level_trend.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/water_level_trend.png')
```

## 2. 水位 + 警戒线折线图

适用：water-situation, water-warning — 显示水位与警戒/保证水位对比。

```python
df['tm'] = pd.to_datetime(df['tm'])   # CSV 读入的 tm 是字符串，必须先转
df = df.dropna(subset=['z'])          # 先洗后画

fig, ax = plt.subplots(figsize=(14, 6))

# 水位线
ax.plot(df['tm'], df['z'], marker='o', markersize=3, color='#2196F3', label='实测水位')

# 警戒水位线（水平虚线）
if df['wrz'].notna().any():
    wrz = df['wrz'].iloc[0]
    ax.axhline(y=wrz, color='#FF9800', linestyle='--', linewidth=2, label=f'警戒水位 {wrz}m')

# 保证水位线
if df['grz'].notna().any():
    grz = df['grz'].iloc[0]
    ax.axhline(y=grz, color='#F44336', linestyle='--', linewidth=2, label=f'保证水位 {grz}m')

# 超警戒区域高亮
if df['wrz'].notna().any():
    ax.fill_between(df['tm'], df['z'], df['wrz'].iloc[0],
                    where=(df['z'] > df['wrz'].iloc[0]),
                    alpha=0.2, color='red', label='超警戒区域')

ax.set_title('水位与警戒水位对比', fontsize=16)
ax.set_xlabel('时间', fontsize=12)
ax.set_ylabel('水位 (m)', fontsize=12)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
plt.xticks(rotation=45)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'water_level_warning.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/water_level_warning.png')
```

## 3. 降雨量柱状图

适用：rainfall — 日降雨量或时段降雨量。

```python
df['tm'] = pd.to_datetime(df['tm'])   # CSV 读入的 tm 是字符串，必须先转
df = df.dropna(subset=['drp'])        # 先洗后画

fig, ax = plt.subplots(figsize=(14, 6))

colors = ['#1976D2' if v < 25 else '#FF9800' if v < 50 else '#F44336'
          for v in df['drp']]

ax.bar(df['tm'], df['drp'], color=colors, width=0.8)
ax.set_title('日降雨量', fontsize=16)
ax.set_xlabel('日期', fontsize=12)
ax.set_ylabel('降雨量 (mm)', fontsize=12)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
plt.xticks(rotation=45)

# 降雨等级参考线
for threshold, label, color in [(25, '大雨 25mm', '#FF9800'), (50, '暴雨 50mm', '#F44336')]:
    ax.axhline(y=threshold, color=color, linestyle=':', alpha=0.6)
    ax.text(df['tm'].iloc[0], threshold + 1, label, fontsize=9, color=color)

ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'rainfall_daily.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/rainfall_daily.png')
```

## 4. 月度降雨量对比柱状图

适用：rainfall — 多年/多月降雨量对比。

```python
df = df.dropna(subset=['total_rain'])   # 先洗后画（x 轴为月份数值，无需 to_datetime）

fig, ax = plt.subplots(figsize=(14, 6))

months = df['month'].unique()
years = df['year'].unique()
bar_width = 0.8 / len(years)

for i, year in enumerate(years):
    year_data = df[df['year'] == year]
    offset = (i - len(years)/2 + 0.5) * bar_width
    ax.bar(year_data['month'] + offset, year_data['total_rain'],
            width=bar_width, label=f'{year}年')

ax.set_title('月度降雨量对比', fontsize=16)
ax.set_xlabel('月份', fontsize=12)
ax.set_ylabel('降雨量 (mm)', fontsize=12)
ax.set_xticks(range(1, 13))
ax.set_xticklabels([f'{m}月' for m in range(1, 13)])
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'rainfall_monthly_compare.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/rainfall_monthly_compare.png')
```

## 5. 水质指标变化趋势图

适用：water-quality — 多指标子图展示水质变化。

```python
df['spt'] = pd.to_datetime(df['spt'])   # CSV 读入的采样时间是字符串，必须先转
df = df.dropna(subset=['spt'])          # 先洗后画（各指标列的 NaN 会自然显示为断点）

indicators = {
    'dox': ('溶解氧 DO (mg/L)', '#4CAF50'),
    'codmn': ('高锰酸盐 CODMn (mg/L)', '#FF9800'),
    'nh3n': ('氨氮 NH3N (mg/L)', '#2196F3'),
    'tp': ('总磷 TP (mg/L)', '#9C27B0')
}

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('水质指标变化趋势', fontsize=16)

for idx, (col, (label, color)) in enumerate(indicators.items()):
    ax = axes[idx // 2][idx % 2]
    ax.plot(df['spt'], df[col], marker='o', markersize=3, color=color)
    ax.set_title(label, fontsize=12)
    ax.set_xlabel('采样时间', fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'water_quality_trend.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/water_quality_trend.png')
```

## 6. 水质等级阶梯图

适用：water-quality, water-warning — 水质等级随时间变化。

```python
df['spt'] = pd.to_datetime(df['spt'])          # CSV 读入的采样时间是字符串，必须先转
df = df.dropna(subset=['grade']).sort_values('spt')   # 先洗后画

grade_colors = {
    'Ⅰ类': '#4CAF50', 'Ⅱ类': '#8BC34A', 'Ⅲ类': '#CDDC39',
    'Ⅳ类': '#FFC107', 'Ⅴ类': '#FF9800', '劣Ⅴ类': '#F44336'
}

fig, ax = plt.subplots(figsize=(14, 5))

for i in range(len(df) - 1):
    grade = df.iloc[i]['grade']
    color = grade_colors.get(grade, '#999999')
    ax.hlines(y=grade, xmin=df.iloc[i]['spt'], xmax=df.iloc[i+1]['spt'],
              colors=color, linewidth=4)

ax.set_title('水质综合等级变化', fontsize=16)
ax.set_xlabel('采样时间', fontsize=12)
ax.set_ylabel('水质等级', fontsize=12)
plt.xticks(rotation=45)
ax.grid(True, alpha=0.3, axis='x')

# 图例
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=c, label=g) for g, c in grade_colors.items()]
ax.legend(handles=legend_elements, fontsize=9, loc='upper right')

plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'water_quality_grade.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/water_quality_grade.png')
```

## 7. 闸泵运行状态面板

适用：gate-pump-operation — 闸门开度 + 泵站流量综合面板。

```python
df_gate = df_gate.dropna(subset=['gtophgt'])   # 先洗后画
df_pump = df_pump.dropna(subset=['pmpq'])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('闸泵运行状态', fontsize=16)

# 左：闸门开度
gate_data = df_gate.sort_values('gtophgt', ascending=True)
colors = ['#4CAF50' if h > 0 else '#BDBDBD' for h in gate_data['gtophgt']]
ax1.barh(gate_data['gtname'], gate_data['gtophgt'], color=colors)
ax1.set_title('闸门开度 (m)', fontsize=12)
ax1.set_xlabel('开度 (m)')
for i, v in enumerate(gate_data['gtophgt']):
    ax1.text(v + 0.01, i, f'{v:.2f}m', va='center', fontsize=9)

# 右：泵站流量
pump_data = df_pump.sort_values('pmpq', ascending=True)
colors = ['#2196F3' if q > 0 else '#BDBDBD' for q in pump_data['pmpq']]
ax2.barh(pump_data['stnm'], pump_data['pmpq'], color=colors)
ax2.set_title('泵站抽水流量 (m³/s)', fontsize=12)
ax2.set_xlabel('流量 (m³/s)')

plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'gate_pump_status.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/gate_pump_status.png')
```

## 8. 预测 vs 实际水位对比图

适用：water-forecast — 预测水位与实测水位对比，含误差区间。

```python
actual_df['tm'] = pd.to_datetime(actual_df['tm'])       # CSV 读入的 tm 是字符串，必须先转
forecast_df['tm'] = pd.to_datetime(forecast_df['tm'])
actual_df = actual_df.dropna(subset=['z'])              # 先洗后画
forecast_df = forecast_df.dropna(subset=['vals'])

fig, ax = plt.subplots(figsize=(14, 6))

# 实测水位
ax.plot(actual_df['tm'], actual_df['z'], marker='o', markersize=3,
        color='#2196F3', label='实测水位', linewidth=2)

# 预测水位
ax.plot(forecast_df['tm'], forecast_df['vals'], marker='s', markersize=3,
        color='#FF9800', label='预测水位', linewidth=2, linestyle='--')

# 误差区间（如果有）
if 'upper' in forecast_df.columns:
    ax.fill_between(forecast_df['tm'], forecast_df['lower'], forecast_df['upper'],
                    alpha=0.15, color='#FF9800', label='预测区间')

ax.set_title('预测水位 vs 实测水位', fontsize=16)
ax.set_xlabel('时间', fontsize=12)
ax.set_ylabel('水位 (m)', fontsize=12)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.xticks(rotation=45)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'forecast_vs_actual.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/forecast_vs_actual.png')
```

## 9. 预警状态汇总面板

适用：water-warning — 各站预警状态一览。

```python
df = df.dropna(subset=['z']).reset_index(drop=True)   # 先洗后画（reset_index 保证 iterrows 的 i 与 barh 行号对齐）

fig, ax = plt.subplots(figsize=(14, max(4, len(df) * 0.5)))

status_colors = {'正常': '#4CAF50', '黄色预警': '#FFC107', '红色预警': '#F44336'}
colors = [status_colors.get(s, '#BDBDBD') for s in df['status']]

ax.barh(df['stnm'], df['z'], color=colors)
for i, row in df.iterrows():
    ax.text(row['z'] + 0.05, i, f"{row['z']:.2f}m ({row['status']})",
            va='center', fontsize=9)

# 警戒水位参考线
if 'wrz' in df.columns:
    for i, row in df.iterrows():
        if pd.notna(row['wrz']):
            ax.plot(row['wrz'], i, 'v', color='orange', markersize=8)

ax.set_title('水位预警状态汇总', fontsize=16)
ax.set_xlabel('水位 (m)', fontsize=12)

from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=c, label=l) for l, c in status_colors.items()]
ax.legend(handles=legend_elements, fontsize=10, loc='lower right')
ax.grid(True, alpha=0.3, axis='x')
plt.tight_layout()
OUT_DIR = '/mnt/user-data/outputs'
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, 'warning_summary.png'), dpi=150, bbox_inches='tight')
print('图表已保存: /mnt/user-data/outputs/warning_summary.png')
```

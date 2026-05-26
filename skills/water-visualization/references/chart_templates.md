# 水利图表模板

> 各类水利场景的 matplotlib 代码模板。替换数据和参数即可使用。

## 公共头部（所有模板必须包含）

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

# CJK 字体设置（必须）
matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
```

---

## 1. 水位趋势折线图

适用：water-situation, water-forecast — 单站或多站水位随时间变化。

```python
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
plt.savefig('water_level_trend.png', dpi=150, bbox_inches='tight')
print('图表已保存: water_level_trend.png')
```

## 2. 水位 + 警戒线折线图

适用：water-situation, water-warning — 显示水位与警戒/保证水位对比。

```python
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
plt.savefig('water_level_warning.png', dpi=150, bbox_inches='tight')
print('图表已保存: water_level_warning.png')
```

## 3. 降雨量柱状图

适用：rainfall — 日降雨量或时段降雨量。

```python
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
plt.savefig('rainfall_daily.png', dpi=150, bbox_inches='tight')
print('图表已保存: rainfall_daily.png')
```

## 4. 月度降雨量对比柱状图

适用：rainfall — 多年/多月降雨量对比。

```python
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
plt.savefig('rainfall_monthly_compare.png', dpi=150, bbox_inches='tight')
print('图表已保存: rainfall_monthly_compare.png')
```

## 5. 水质指标变化趋势图

适用：water-quality — 多指标子图展示水质变化。

```python
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
plt.savefig('water_quality_trend.png', dpi=150, bbox_inches='tight')
print('图表已保存: water_quality_trend.png')
```

## 6. 水质等级阶梯图

适用：water-quality, water-warning — 水质等级随时间变化。

```python
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
plt.savefig('water_quality_grade.png', dpi=150, bbox_inches='tight')
print('图表已保存: water_quality_grade.png')
```

## 7. 闸泵运行状态面板

适用：gate-pump-operation — 闸门开度 + 泵站流量综合面板。

```python
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
plt.savefig('gate_pump_status.png', dpi=150, bbox_inches='tight')
print('图表已保存: gate_pump_status.png')
```

## 8. 预测 vs 实际水位对比图

适用：water-forecast — 预测水位与实测水位对比，含误差区间。

```python
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
plt.savefig('forecast_vs_actual.png', dpi=150, bbox_inches='tight')
print('图表已保存: forecast_vs_actual.png')
```

## 9. 预警状态汇总面板

适用：water-warning — 各站预警状态一览。

```python
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
plt.savefig('warning_summary.png', dpi=150, bbox_inches='tight')
print('图表已保存: warning_summary.png')
```

# water-visualization matplotlib 美化设计（A 风格·极简现代）

> 日期: 2026-08-06 ｜ 状态: 已确认，待实现
> 关联: 屏蔽 chart-visualization（生产无外网）；water-visualization 成为唯一可视化路径

## 背景

`chart-visualization`（AntV / JS）依赖云端 `antv-studio.alipay.com` 渲染：① 生产环境无外网会直接失效；② 每次画图把水利数据 POST 给第三方（合规风险）；③ 其 line/area/dual_axes 只接受 `time/value/group` 等基础字段，**画不了警戒水位线/超警区域高亮**。已于 2026-08-06 将其移至 `skills/_disabled/` 屏蔽。

屏蔽后 `water-visualization`（matplotlib）成为唯一可视化 skill。其图表当前是 matplotlib 默认样式 + 硬编码 Material Design 色（`#2196F3`/`#FF9800`/`#F44336`/`#4CAF50`），视觉偏朴素。目标：升级为对标 AntV 的现代精致感，同时保留水利语义与稳定性。

## 目标

把 `chart_templates.md` 的图表"皮肤"升级为 **A 风格（极简现代）**，并满足：
- 零数据外传（本地 matplotlib 渲染）
- 保留所有水利语义（警戒线 `axhline`、超警高亮 `fill_between`、降雨分级色、水质等级色阶）
- 保留所有踩坑验证铁律（查画解耦、`write_file` 落盘、`dropna` 先洗后画、`to_datetime`、`OUT_DIR`）
- 最小侵入，LLM 照抄即用（模板保持自包含）

## 环境约束（已验证）

- **matplotlib 3.11.0** 在 DeerFlow 沙箱的 backend venv（`/opt/git/deer-flow/backend/.venv`）；沙箱为 `LocalSandboxProvider`（`subprocess.run` host bash，无 shell），沙箱内 `python3` 走该 venv。
- **字体实际安装 `Noto Sans CJK JP`**（非 SC）。JP 含 CJK 汉字字形，简体中文渲染正常（2026-08-06 + 7月16日实测均通过）。
- host 顶层 `python3`（hermes venv）无 matplotlib——仅沙箱 venv 可用，验证样图须用 backend venv python。

## 设计（方案①：公共头部 + PALETTE，全局生效）

### 1. 公共头部 + 黄金模板升级

新增 A 风格 `rcParams` + 配色常量（公共头部与黄金模板均包含）：

```python
plt.rcParams.update({
    'axes.spines.top': False, 'axes.spines.right': False,        # 去顶/右框
    'axes.edgecolor': '#bfbfbf', 'axes.linewidth': 0.8,
    'axes.labelcolor': '#595959', 'axes.titleweight': 600,        # 600 消 semibold 警告
    'xtick.color': '#8c8c8c', 'ytick.color': '#8c8c8c',
    'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'legend.frameon': False,
    'font.sans-serif': ['Noto Sans CJK JP', 'Noto Sans CJK SC',   # JP=实际安装首选；SC 兼容
                        'WenQuanYi Micro Hei', 'DejaVu Sans'],
})
PALETTE = ['#5B8FF9', '#5AD8A6', '#5D7092', '#F6BD16',
           '#E8684A', '#6DC8EC', '#9270CA']                       # AntV 多系列色板
NORMAL, WARN, DANGER = '#52C41A', '#FAAD14', '#F4664A'            # 语义色：正常/警戒/保证·超警
```

网格样式：`ax.grid(True, axis='y', alpha=0.3, linestyle='--', color='#d9d9d9')`（淡虚线）。
标题：`fontsize=14, color='#262626', pad=14`。

### 2. 9 个模板颜色映射（水利逻辑一行不动，只换色）

| 模板 | 当前硬编码色 | → A 风格 |
|---|---|---|
| ①水位趋势 / ④月度降雨 / ⑤水质多指标 / ⑧预测对比 | 默认色轮转 | 多系列 → `PALETTE` 轮转 |
| ②水位+警戒线 | `#2196F3`/`#FF9800`/`#F44336` | 水位 `#5B8FF9` / 警戒 `WARN` / 保证 `DANGER` / 超警 fill `DANGER` α0.15 |
| ③降雨柱分级 | `#1976D2`/`#FF9800`/`#F44336` | <25 `#5B8FF9` / <50 `#F6BD16` / ≥50 `#E8684A`；参考线 `WARN`/`DANGER` |
| ⑥水质等级阶梯 | `#4CAF50`…`#F44336` | Ⅰ→劣Ⅴ 绿→黄→红柔和渐变，例：`['#5AD8A6','#A0D911','#F6BD16','#FAAD14','#FA8C16','#E8684A']`（Ⅰ/Ⅱ/Ⅲ/Ⅳ/Ⅴ/劣Ⅴ） |
| ⑦闸泵面板 | `#4CAF50`/`#BDBDBD`、`#2196F3`/`#BDBDBD` | 运行 `#5AD8A6` / 停 `#BFBFBF` |
| ⑨预警汇总 | `#4CAF50`/`#FFC107`/`#F44336` | 正常 `NORMAL` / 黄警 `WARN` / 红警 `DANGER` |

### 3. 保留不动（骨架）

`axhline` 警戒线、`fill_between` 超警高亮、`dropna(subset=...)` 先洗后画、`pd.to_datetime` 时间列转换、`OUT_DIR` 绝对路径、查画解耦（CSV 中转）、`write_file` 落盘铁律、CJK 字体处理——**只换皮肤，不动骨架**。

### 4. 字体说明文案修正

公共头部"字体说明"段落更新：实测安装 `Noto Sans CJK JP`（非 `WenQuanYi`/`SimHei`，也非 SC）；字体列表以 JP 首选。消除旧文案"未装 WenQuanYi"的误导。

## 范围

- **改**：`skills/water-visualization/references/chart_templates.md`（公共头部 + 黄金模板 + 9 模板颜色 + 字体说明）
- **可选小改**：`skills/water-visualization/SKILL.md`（Supported Technologies / Best Practices 提及新配色——非必需）

## 不做（out of scope）

- 不改任何水利查询/聚合/分析逻辑
- 不抽 `references/style.py`（保持模板自包含、照抄即用）
- 不改模板结构 / 子图布局 / fig 尺寸
- 不动其他 skill，不动 chart-visualization（已屏蔽）

## 验证

1. 改完后用 backend venv python 对每个模板生成样图，目视确认：中文正常、配色统一为 AntV 风、水利语义（警戒线/超警/分级色）保留。
2. 重点确认模板②（水位+警戒线+超警高亮）与模板⑥（水质等级渐变）。
3. 改前/改后同数据对比（已有改前样图 baseline）。

## 风险

- **低**：颜色替换是机械改动，逻辑不变。主要风险是漏改某个硬编码色 → 验证时逐模板 grep 检查 `#` 色值。
- **字体 JP vs SC**：已实测 JP 渲染中文正常；字体列表保留 SC 作兼容兜底。
- **回归**：9 个模板均经历史踩坑验证，改动须严格限定在颜色/rcParams，不动数据流——review 时逐行核对。

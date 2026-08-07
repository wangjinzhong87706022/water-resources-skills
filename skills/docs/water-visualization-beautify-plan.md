# water-visualization A 风格美化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `water-visualization/references/chart_templates.md` 的图表从 matplotlib 默认样式 + Material 硬编码色升级为 A 风格（AntV 配色 + 极简现代），水利逻辑一行不动。

**Architecture:** 只改 `chart_templates.md`：公共头部新增 A 风 `rcParams` + `PALETTE`/语义色常量；黄金模板 + 9 个模板把硬编码颜色替换为常量/新色值。不抽 `style.py`，模板保持自包含、照抄即用。

**Tech Stack:** matplotlib 3.11.0（DeerFlow backend venv）、Markdown 代码模板。spec：`skills/docs/water-visualization-beautify-design.md`。

## Global Constraints

- **只动颜色/rcParams，不动水利逻辑**：`axhline` 警戒线、`fill_between` 超警、`dropna` 先洗后画、`pd.to_datetime`、`OUT_DIR`、查画解耦、`write_file` 落盘铁律、CJK 字体处理——全部保留原样。
- **验证用 backend venv python**：`/opt/git/deer-flow/backend/.venv/bin/python`（唯一有 matplotlib 3.11 的环境；host 顶层 `python3`/hermes venv/系统 python 均无 matplotlib）。
- **字体首选 `Noto Sans CJK JP`**（实测安装的就是它，非 SC；JP 含汉字字形，中文渲染正常）。
- **验证方式 = 渲染样图目视**，非 pytest：每个模板用模拟数据生成 PNG，确认①中文不方块②配色统一为 AntV 风③水利语义保留。
- **不主动 commit**：本项目按惯例仅在用户指示时提交；各 task 的 commit 步骤执行时改为"询问用户是否提交"或跳过。
- 配色常量（公共头部定义，后续 task 引用）：
  - `PALETTE = ['#5B8FF9','#5AD8A6','#5D7092','#F6BD16','#E8684A','#6DC8EC','#9270CA']`
  - `NORMAL, WARN, DANGER = '#52C41A', '#FAAD14', '#F4664A'`

## File Structure

- **Modify:** `skills/water-visualization/references/chart_templates.md`（公共头部 + 黄金模板 + 9 个模板代码块 + 字体说明文案）
- **Optional Modify:** `skills/water-visualization/SKILL.md`（Supported Technologies/Best Practices 提及新配色——Task 6，非必需）
- **验证脚本:** `/tmp/verify_wviz.py`（临时，Task 6 用，不入库）

---

### Task 1: 公共头部 + 配色常量 + 字体说明

**Files:**
- Modify: `skills/water-visualization/references/chart_templates.md` 公共头部代码块（约行 7-22）+ 字体说明段（约行 24）

**Interfaces:**
- Produces: `PALETTE`、`NORMAL`/`WARN`/`DANGER` 常量 + A 风 `rcParams`，供 Task 2-5 的所有模板引用。

- [ ] **Step 1: 编辑公共头部代码块**，在 `os.makedirs(OUT_DIR, ...)` 之前插入 rcParams + 常量，并改字体列表：

```python
# A 风格 rcParams（极简现代，对标 AntV）
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
plt.rcParams['axes.unicode_minus'] = False
# AntV 配色
PALETTE = ['#5B8FF9', '#5AD8A6', '#5D7092', '#F6BD16', '#E8684A', '#6DC8EC', '#9270CA']
NORMAL, WARN, DANGER = '#52C41A', '#FAAD14', '#F4664A'  # 正常/警戒/保证·超警
```

- [ ] **Step 2: 修改字体列表行**：把 `matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans']` 整行删除（已并入上面 rcParams）。

- [ ] **Step 3: 更新字体说明文案**（约行 24 那段 `> **字体说明...`），改为：

```
> **字体说明（重要）**：宿主机实测安装的是 `Noto Sans CJK JP`（不是 SC，也非 WenQuanYi/SimHei）。JP 含 CJK 汉字字形，简体中文渲染正常（实测通过）。字体列表以 JP 首选、SC 兼容兜底，不要改、不要花时间找别的字体。乱码只因用错字体名。
```

- [ ] **Step 4: 验证公共头部语法** —— 用 backend venv 跑公共头部片段，确认无报错：

```bash
/opt/git/deer-flow/backend/.venv/bin/python -c "
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
exec(open('/dev/stdin').read())
" <<'EOF'
plt.rcParams.update({'axes.spines.top': False,'axes.titleweight': 600,'font.sans-serif':['Noto Sans CJK JP','DejaVu Sans']})
PALETTE=['#5B8FF9','#5AD8A6']; NORMAL,WARN,DANGER='#52C41A','#FAAD14','#F4664A'
import matplotlib.pyplot as plt; fig,ax=plt.subplots(); ax.plot([1,2],[1,2]); plt.close()
print('OK: 公共头部语法通过')
EOF
```
Expected: `OK: 公共头部语法通过`

- [ ] **Step 5: 询问是否提交**（项目惯例不自动 commit）。

---

### Task 2: 黄金模板升级（A 风标杆）

**Files:**
- Modify: `chart_templates.md` 黄金模板代码块（约行 46-81）

**Interfaces:**
- Consumes: Task 1 的 rcParams + PALETTE
- Produces: 黄金模板作为"照抄即用"的 A 风标杆，示范给 LLM。

- [ ] **Step 1: 编辑黄金模板**：
  - 在黄金模板的 `import` 之后、`# ---- 只改这 4 处 ----` 之前，插入 Task 1 的 rcParams + `PALETTE` 定义（黄金模板必须自包含，不能假设公共头部已加载）。
  - 折线循环颜色改为 PALETTE 轮转：`ax.plot(g[X_COL], g[Y_COL], marker='o', color=PALETTE[idx % len(PALETTE)], label=f'{key}')`（循环带 `enumerate`）。
  - 网格行改为淡虚线：`ax.grid(True, axis='y', alpha=0.3, linestyle='--', color='#d9d9d9')`。
  - 标题行加颜色/pad：`ax.set_title(TITLE, fontsize=14, color='#262626', pad=14)`。
  - 字体列表行同步改为 JP 首选（与 Task 1 一致）。

- [ ] **Step 2: 验证黄金模板可跑** —— 抽取黄金模板核心，喂模拟数据，确认出图：

```bash
/opt/git/deer-flow/backend/.venv/bin/python -c "
import pandas as pd
df = pd.DataFrame({'mo':[1,2,3,1,2,3],'avg_z':[4.5,4.6,4.7,5.1,5.0,4.9],'yr':['A','A','A','B','B','B']})
df.to_csv('/tmp/gt.csv', index=False)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':600,'font.sans-serif':['Noto Sans CJK JP','DejaVu Sans']})
PALETTE=['#5B8FF9','#5AD8A6','#5D7092']
df=pd.read_csv('/tmp/gt.csv'); fig,ax=plt.subplots(figsize=(11,5))
for idx,(key,g) in enumerate(df.groupby('yr')):
    g=g.sort_values('mo'); ax.plot(g['mo'],g['avg_z'],marker='o',color=PALETTE[idx%len(PALETTE)],label=key)
ax.set_title('测试',fontsize=14,color='#262626',pad=14); ax.grid(True,axis='y',alpha=0.3,linestyle='--',color='#d9d9d9')
plt.savefig('/tmp/golden_test.png',dpi=150); print('OK 黄金模板出图')
"
```
Expected: `OK 黄金模板出图`

- [ ] **Step 3: 询问是否提交。**

---

### Task 3: 模板①②③换色（水位趋势 / 水位+警戒线 / 降雨柱）

**Files:** Modify `chart_templates.md` 模板①（约行 91-113）、模板②（约行 119-156）、模板③（约行 162-189）

**Interfaces:** Consumes Task 1 的 `PALETTE`/`WARN`/`DANGER`（模板②③位于公共头部之后，可直接引用常量；若 LLM 单抄某模板，需把用到的常量值内联注释）。

- [ ] **Step 1: 模板①水位趋势**：多站循环颜色 `ax.plot(..., color=PALETTE[idx % len(PALETTE)], ...)`（加 `enumerate`）。网格行改淡虚线；标题加 `color='#262626', pad=14`。

- [ ] **Step 2: 模板②水位+警戒线**，颜色替换（逻辑不动）：
  - 水位线 `color='#2196F3'` → `color='#5B8FF9'`
  - 警戒线 `color='#FF9800'` → `color=WARN`（`#FAAD14`）
  - 保证线 `color='#F44336'` → `color=DANGER`（`#F4664A`）
  - 超警 fill `color='red'` → `color=DANGER`（`#F4664A`，alpha 维持 0.2）
  - 网格淡虚线；标题加色/pad。

- [ ] **Step 3: 模板③降雨柱**，分级色替换：
  - `colors = ['#1976D2' if v<25 else '#FF9800' if v<50 else '#F44336' ...]` → `['#5B8FF9' if v<25 else '#F6BD16' if v<50 else '#E8684A' for v in df['drp']]`
  - 参考线循环 `(25,'大雨 25mm','#FF9800'),(50,'暴雨 50mm','#F44336')` → `...(25,'大雨 25mm',WARN),(50,'暴雨 50mm',DANGER)`
  - 网格淡虚线；标题加色/pad。

- [ ] **Step 4: 验证三模板配色** —— grep 确认旧色已清：`grep -nE '#2196F3|#FF9800|#F44336|#1976D2' chart_templates.md` 应只在模板④-⑨出现（本 task 范围内已无）。

- [ ] **Step 5: 询问是否提交。**

---

### Task 4: 模板④⑤⑥换色（月度降雨对比 / 水质指标 / 水质等级阶梯）

**Files:** Modify `chart_templates.md` 模板④（约行 195-222）、模板⑤（约行 228-256）、模板⑥（约行 262-295）

- [ ] **Step 1: 模板④月度降雨对比**：多年循环 `label=f'{year}年'` 的柱颜色 → 用 `PALETTE[i % len(PALETTE)]`（替换无显式 color 的 `ax.bar(...)`，加 `color=`）。

- [ ] **Step 2: 模板⑤水质指标**：`indicators` 字典的硬编码色替换为 PALETTE：
  ```python
  indicators = {
      'dox':   ('溶解氧 DO (mg/L)', PALETTE[0]),
      'codmn': ('高锰酸盐 CODMn (mg/L)', PALETTE[3]),
      'nh3n':  ('氨氮 NH3N (mg/L)', PALETTE[1]),
      'tp':    ('总磷 TP (mg/L)', PALETTE[6]),
  }
  ```

- [ ] **Step 3: 模板⑥水质等级阶梯**：`grade_colors` 换为柔和绿→黄→红渐变：
  ```python
  grade_colors = {
      'Ⅰ类': '#5AD8A6', 'Ⅱ类': '#A0D911', 'Ⅲ类': '#F6BD16',
      'Ⅳ类': '#FAAD14', 'Ⅴ类': '#FA8C16', '劣Ⅴ类': '#E8684A'
  }
  ```

- [ ] **Step 4: 验证** —— grep 确认本范围旧色已清：`grep -nE '#4CAF50|#8BC34A|#CDDC39|#FFC107' chart_templates.md` 应只剩模板⑦/⑨（若⑦⑨用同色）。

- [ ] **Step 5: 询问是否提交。**

---

### Task 5: 模板⑦⑧⑨换色（闸泵面板 / 预测对比 / 预警汇总）

**Files:** Modify `chart_templates.md` 模板⑦（约行 301-329）、模板⑧（约行 335-368）、模板⑨（约行 374-405）

- [ ] **Step 1: 模板⑦闸泵面板**：状态色替换：
  - 闸门 `colors = ['#4CAF50' if h>0 else '#BDBDBD' ...]` → `['#5AD8A6' if h>0 else '#BFBFBF' for h in gate_data['gtophgt']]`
  - 泵站 `colors = ['#2196F3' if q>0 else '#BDBDBD' ...]` → `['#5B8FF9' if q>0 else '#BFBFBF' for q in pump_data['pmpq']]`

- [ ] **Step 2: 模板⑧预测对比**：
  - 实测 `color='#2196F3'` → `color='#5B8FF9'`
  - 预测 `color='#FF9800'` → `color='#F6BD16'`
  - 预测区间 fill `color='#FF9800'` → `color='#F6BD16'`

- [ ] **Step 3: 模板⑨预警汇总**：`status_colors = {'正常':'#4CAF50','黄色预警':'#FFC107','红色预警':'#F44336'}` → `{'正常':NORMAL,'黄色预警':WARN,'红色预警':DANGER}`（即 `#52C41A`/`#FAAD14`/`#F4664A`）。

- [ ] **Step 4: 终极 grep** —— 全文不应再有旧 Material 色：`grep -nE '#2196F3|#FF9800|#F44336|#4CAF50|#1976D2|#FFC107|#8BC34A|#CDDC39' chart_templates.md` 应为空（或仅在"改前对比"说明里）。逐条确认无遗漏。

- [ ] **Step 5: 询问是否提交。**

---

### Task 6: 整体渲染验证 + SKILL.md 可选更新

**Files:**
- Test: `/tmp/verify_wviz.py`（临时验证脚本）
- Optional Modify: `skills/water-visualization/SKILL.md`

- [ ] **Step 1: 写验证脚本**，对每个模板用模拟数据渲染 PNG（脚本骨架：逐模板构造最小 DataFrame → 贴入该模板代码 → savefig 到 /tmp/verify_N.png）。重点覆盖模板②（警戒线+超警）、模板⑥（等级渐变）。

- [ ] **Step 2: 跑验证脚本**：
```bash
/opt/git/deer-flow/backend/.venv/bin/python /tmp/verify_wviz.py
```
Expected: 9 张 PNG 生成，无异常。

- [ ] **Step 3: 目视确认**（用 analyze_image 或人工）：每张图①中文不方块②配色为 AntV 柔和风③警戒线/超警高亮/分级色保留。重点看模板②超警 fill_between 红色高亮在、模板⑥六色渐变对。

- [ ] **Step 4（可选）: SKILL.md 小更新** —— 若 SKILL.md 的 Supported Technologies/Best Practices 提到具体配色或 matplotlib 样式，同步一句"图表默认 AntV 风配色（PALETTE），详见 chart_templates.md"。非必需，无则跳过。

- [ ] **Step 5: 清理临时文件** `rm /tmp/verify_wviz.py /tmp/verify_*.png /tmp/golden_test.png /tmp/viz_sample*.png`。

- [ ] **Step 6: 汇报 + 询问是否整体提交。**

---

## Self-Review（写计划后自检）

**1. Spec coverage：** spec 的「公共头部 rcParams/PALETTE/语义色」「9 模板颜色映射表」「字体说明修正」「范围仅 chart_templates.md」「验证=渲染样图」→ 分别由 Task 1/3-5/1/(全局)/6 覆盖。✓ 无遗漏。
**2. Placeholder 扫描：** 每个 task 都给了具体色值 before→after 和定位，无 TBD/TODO。✓
**3. 一致性：** PALETTE/语义色值在 Task 1 定义，Task 3-5 引用值一致（`#5B8FF9`/`#FAAD14`/`#F4664A` 等）。字体 JP 首选在 Task 1/2 一致。✓

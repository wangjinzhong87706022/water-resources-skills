# 水利 Skill 使用与测试指南

> 覆盖 7 个数据 skill + 1 个可视化 skill + shared 共享资源的使用方法和验证步骤

---

## 一、基本使用

### 1.1 确认 skill 已安装

```bash
hermes skills list | grep water
```

预期输出 7 个 skill：

```
water-situation      水情综合查询
rainfall             雨情综合查询
water-quality        水质综合查询
water-forecast       水位预测与模型计算
gate-pump-operation  闸泵工况查询
water-warning        水利预警
water-visualization  水利数据可视化
```

### 1.2 单 skill 使用

```bash
# 斜杠命令（交互模式）
$ hermes
> /water-situation 古运河有哪些水位测站

# 单次查询模式（非交互，结果直接输出到终端）
hermes -z -s water-situation "古运河有哪些水位测站"

# 预加载模式（交互 session 内持续使用该 skill）
hermes -s water-situation
> 古运河有哪些水位测站
> 宝应水位站最近30天水位数据
```

### 1.3 多 skill 组合使用

数据 skill 与可视化 skill 组合，一次完成"查询 + 画图"：

```bash
# 预加载两个 skill
hermes -s water-situation,water-visualization
> 查询古运河最近30天水位，画个趋势图

# 单次模式
hermes -z -s water-situation,water-visualization "查询古运河最近30天水位并画折线图"

# 降雨 + 可视化
hermes -z -s rainfall,water-visualization "2024年扬州城区月降雨量柱状图"

# 水质 + 可视化
hermes -z -s water-quality,water-visualization "最近一个月瘦西湖水质变化趋势图"

# 预警 + 可视化
hermes -z -s water-warning,water-visualization "当前各站预警状态汇总图"

# 闸泵 + 可视化
hermes -z -s gate-pump-operation,water-visualization "查询所有闸站启闭状态面板"
```

### 1.4 LLM 自动串联

不预加载 skill，LLM 根据问题自动选择：

```bash
$ hermes
> 查询古运河最近30天水位并画图
（LLM 自动: skill_view("water-situation") → 查询 → skill_view("water-visualization") → 画图）
```

---

## 二、可视化 Skill 专项使用

### 2.1 三种触发方式

```bash
# 方式 1：单独使用（上下文中需已有数据）
$ hermes
> /water-situation 查询古运河最近30天水位数据
（返回表格数据）
> /water-visualization 把上面的水位数据画成折线图

# 方式 2：预加载组合（推荐）
hermes -s water-situation,water-visualization
> 查询古运河最近30天水位并画趋势图

# 方式 3：在数据查询中直接要求画图
hermes -z -s water-situation,water-visualization "古运河最近30天水位趋势图"
```

### 2.2 支持的图表类型

| 图表类型 | 适用场景 | 对应数据 Skill |
|---------|---------|---------------|
| 水位趋势折线图 | 单站/多站水位随时间变化 | water-situation |
| 水位 + 警戒线图 | 水位与警戒/保证水位对比 | water-situation, water-warning |
| 降雨量柱状图 | 日降雨量（颜色分级） | rainfall |
| 月度降雨对比图 | 多年/多月降雨量对比 | rainfall |
| 水质指标趋势图 | DO/CODMn/NH3N/TP 四子图 | water-quality |
| 水质等级阶梯图 | 水质综合等级随时间变化 | water-quality, water-warning |
| 预测 vs 实际图 | 预测水位与实测水位对比 | water-forecast |
| 闸泵运行面板 | 闸门开度 + 泵站流量 | gate-pump-operation |
| 预警状态汇总 | 各站预警状态一览 | water-warning |

### 2.3 图表示例

```bash
# 水位趋势折线图
hermes -z -s water-situation,water-visualization "查询古运河最近30天水位，画折线图"

# 降雨量柱状图（蓝/橙/红颜色分级）
hermes -z -s rainfall,water-visualization "2024年扬州城区月降雨量柱状图"

# 水质四指标子图
hermes -z -s water-quality,water-visualization "最近一个月瘦西湖水质指标变化趋势图"

# 预警状态面板（绿=正常/黄=超警戒/红=超保证）
hermes -z -s water-warning,water-visualization "当前各站预警状态汇总图"

# 闸泵运行状态面板
hermes -z -s gate-pump-operation,water-visualization "所有闸站启闭状态面板"
```

---

## 三、质量自检功能

每个 skill 的 Workflow 末尾已增加"质量自检"步骤，自动生效，无需用户操作。

### 3.1 自动生效的行为

| 场景 | 自动行为 |
|------|---------|
| SQL 安全检查 | 只允许 SELECT/SHOW/DESCRIBE，禁止写操作 |
| 全表扫描防护 | 必须包含 WHERE 条件（时间范围或测站过滤） |
| JOIN 笛卡尔积防护 | 所有 JOIN 必须有 ON 条件 |
| 结果集限制 | 大数据量查询自动加 LIMIT |
| 空结果自动重试 | 扩大时间范围 → 模糊匹配名称 → 检查别名 |
| 数值合理性检查 | 水位 -1~20m、降雨 0~500mm、流量非负 |

### 3.2 验证质量自检

```bash
# 测试空结果自动重试（2026年无数据，应自动扩大范围或提示）
hermes -z -s water-situation "查询2026年古运河水位站点的数量"

# 测试模糊匹配（用不精确的名称查询，应自动 LIKE 匹配）
hermes -z -s water-situation "查询运河水位"
# 预期：自动匹配到"古运河"、"里运河"等

# 测试数值合理性标注
hermes -z -s rainfall "扬州城区历史最大单日降雨量"
# 预期：若极端值 > 200mm 应标注"极端降雨"

# 测试预测数据时效性提示
hermes -z -s water-forecast "查询未来24小时扬州市重点河道水位预测"
# 预期：若最新预测任务过期，应告知"预测数据非实时"
```

---

## 四、测试验证

### 4.1 快速验证（5 分钟）

```bash
# 1. 确认 7 个 skill 被识别
hermes skills list 2>/dev/null | grep -c water
# 预期: 7

# 2. 验证 shared 文件存在
ls /root/.hermes/skills/water-resources/shared/*.md | wc -l
# 预期: 3

# 3. 验证可视化模板存在
ls /root/.hermes/skills/water-resources/water-visualization/references/chart_templates.md
# 预期: 文件存在

# 4. 跑一个最简单的查询
hermes -z -s water-situation "查询测站总数"

# 5. 跑一个可视化查询
hermes -z -s water-situation,water-visualization "古运河最近30天水位趋势图"
# 预期: 生成 .png 图片文件
```

### 4.2 逐 skill 验证

每个 skill 用一个代表性问题验证：

```bash
# water-situation
hermes -z -s water-situation "古运河有哪些水位测站"

# rainfall
hermes -z -s rainfall "查询扬州城区今日降雨量"

# water-quality
hermes -z -s water-quality "瘦西湖水质当前如何"

# water-forecast
hermes -z -s water-forecast "查询最新预测任务的状态"

# gate-pump-operation
hermes -z -s gate-pump-operation "查询所有闸站最新启闭状态"

# water-warning
hermes -z -s water-warning "查询当前超警戒水位的站点"

# water-visualization（需要配合数据 skill）
hermes -z -s rainfall,water-visualization "2024年扬州城区月降雨量柱状图"
```

### 4.3 可视化专项验证

逐图表类型验证，确认中文渲染正常、颜色正确：

```bash
hermes -z -s water-situation,water-visualization "古运河最近30天水位趋势折线图"
hermes -z -s rainfall,water-visualization "2024年扬州城区月降雨量柱状图"
hermes -z -s water-quality,water-visualization "瘦西湖最近一个月水质指标变化图"
hermes -z -s water-warning,water-visualization "当前各站预警状态汇总图"
hermes -z -s gate-pump-operation,water-visualization "所有闸站启闭状态面板"
hermes -z -s water-forecast,water-visualization "预测水位与实测水位对比图"
```

检查点：
- .png 文件成功生成
- 中文标题/轴标签正常显示（非方块 □□□）
- 图表颜色区分清晰
- 数据点与数据库查询结果一致

### 4.4 批量回归测试

用 `docs/questions.md` 中的 98 道题做批量验证：

```bash
# 将问题列表转为 JSONL 格式用于 batch_runner
# 每行格式: {"prompt": "问题文本"}

# 验证 water-situation 的 25 题
hermes -z -s water-situation "古运河有哪些水位测站"
hermes -z -s water-situation "查询测站总数"
# ... 逐题或批量
```

---

## 五、文件结构参考

```
skills/water-resources/
├── shared/                              # 共享资源（所有 skill 通用）
│   ├── sql_safety_rules.md              #   SQL 安全规则
│   ├── sql_quality_check.md             #   SQL 质量审查流程（4步）
│   ├── db_connection.md                 #   数据库连接信息
│   └── common_schema/
│       ├── st_stbprp_b.md              #   测站基础表（6 skill 共用）
│       └── st_rvfcch_b.md              #   防洪指标表（3 skill 共用）
│
├── water-visualization/                 # 可视化 skill（独立）
│   ├── SKILL.md
│   └── references/
│       └── chart_templates.md           #   9 种水利图表模板
│
├── water-situation/                     # 数据 skill（6 个）
├── rainfall/
├── water-quality/
├── water-forecast/
├── gate-pump-operation/
├── water-warning/
│
└── docs/
    ├── how-to-ask-in-hermes.md          # CLI 提问指南
    ├── usage-and-testing.md             # 本文档
    ├── questions.md                     # 98 道测试题
    └── test-cases-with-sql.md           # 完整测试用例（含 SQL）
```

---

## 六、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `hermes skills list` 没有显示 water-visualization | 文件未同步到 ~/.hermes/ | `cp -r skills/water-resources/water-visualization ~/.hermes/skills/water-resources/` |
| 图表中文显示为方块 □□□ | matplotlib 缺少 CJK 字体 | `apt install fonts-noto-cjk` |
| 查询返回空结果 | 时间范围或名称匹配问题 | 质量自检应自动重试；若仍未返回，尝试用精确站名 |
| 可视化 skill 未被触发 | 未与数据 skill 组合 | 使用 `-s water-situation,water-visualization` 或先查数据再用 `/water-visualization` |
| SQL 安全规则未生效 | shared/ 文件未被加载 | 确认 `/root/.hermes/skills/water-resources/shared/` 目录存在 |

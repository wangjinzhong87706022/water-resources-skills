# Hermes CLI 提问指南

在 hermes CLI 中使用水利 skill 有三种方式。

---

## 方式 1：斜杠命令（推荐）

启动 CLI 后，直接输入 `/skill名 问题`：

```bash
$ hermes

# 水位查询
> /water-situation 古运河有哪些水位测站
> /water-situation 查询宝应水位站最近30天水位数据
> /water-situation 2024年古运河平均水位

# 降雨查询
> /rainfall 2024年扬州城区降雨总量大概是多少
> /rainfall 扬州城区今日降雨量
> /rainfall 对比2023年和2024年扬州城区各月降雨量

# 水质查询
> /water-quality 瘦西湖水质当前如何
> /water-quality 最近一个月瘦西湖水质变化趋势
> /water-quality 查询京杭运河水质等级

# 水位预测
> /water-forecast 未来24小时扬州市重点河道水位预测
> /water-forecast 预测瘦西湖未来24小时水位变化
> /water-forecast 查询最新预测任务的状态

# 闸泵工况
> /gate-pump-operation 查询所有闸站最新启闭状态
> /gate-pump-operation 念四闸站上下游水位和过闸流量
> /gate-pump-operation 泵站综合运行状态汇总

# 水利预警
> /water-warning 哪些站点超警戒水位
> /water-warning 防洪预警汇总
> /water-warning 查询水质低于Ⅳ类的站点
```

hermes 会自动：
1. 加载对应 skill 的 SKILL.md 作为指令上下文
2. 注入 references/ 目录下的 schema.md、business_rules.md、few_shots.md
3. LLM 根据这些知识生成正确的 SQL
4. 调用 MySQL 工具执行 SQL 并返回结果

---

## 方式 2：预加载 skill 启动

启动时通过 `-s` 参数预先加载 skill，之后直接用自然语言提问：

```bash
# 加载单个 skill
$ hermes -s water-situation
> 古运河有哪些水位测站

# 加载多个 skill（逗号分隔）
$ hermes -s water-situation,rainfall,water-warning
> 古运河有哪些水位测站
> 扬州城区降雨量
> 哪些站点超警戒水位

# 也可以多次使用 -s
$ hermes -s water-situation -s rainfall -s water-warning

# 使用 chat 子命令
$ hermes chat -s water-situation,water-quality
> 古运河水位
> 瘦西湖水质如何
```

预加载后不需要再输斜杠命令，直接输入自然语言即可。

---

## 方式 3：LLM 自动选择 skill

不指定 skill，直接输入自然语言问题。hermes 会通过 `skill_view` 工具自动识别问题类型并加载匹配的 skill：

```bash
$ hermes

> 古运河有哪些水位测站
（LLM 自动调用 skill_view(name="water-situation")，加载水位查询 skill）

> 扬州城区今日降雨量
（LLM 自动调用 skill_view(name="rainfall")，加载降雨查询 skill）

> 瘦西湖水质当前如何
（LLM 自动调用 skill_view(name="water-quality")，加载水质查询 skill）
```

---

## 三种方式对比

| 维度 | 斜杠命令 | 预加载 `-s` | 自动选择 |
|------|---------|------------|---------|
| **命令格式** | `/water-situation 问题` | `hermes -s water-situation` | 直接输入问题 |
| **skill 指定** | 用户手动指定 | 用户启动时指定 | LLM 自动判断 |
| **准确性** | 最高，精确匹配 | 高，限定范围内匹配 | 依赖 LLM 判断，可能选错 |
| **便捷性** | 需要记住 skill 名 | 启动时一次性配置 | 最简单，无需记忆 |
| **适用场景** | 单次精确查询 | 专注某类问题的 session | 快速探索、不确定分类 |

---

## 完整 skill 列表

| 斜杠命令 | Skill 名称 | 用途 |
|---------|-----------|------|
| `/water-situation` | 实时水位查询 | 河道/水库水位、防洪指标、超警戒判断 |
| `/rainfall` | 降雨查询 | 雨量数据、短临降雨预测、历史降雨统计 |
| `/water-quality` | 水质查询 | 水质指标、水质等级评价、水质趋势 |
| `/water-forecast` | 水位预测 | 未来水位预报、预测任务管理、断面数据 |
| `/gate-pump-operation` | 闸泵工况 | 闸门启闭、泵站运行、上下游水位 |
| `/water-warning` | 水利预警 | 超警戒/超保证判断、防洪汇总、水质预警 |

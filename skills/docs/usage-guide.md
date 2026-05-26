# 水利 Skill 测试用例使用指南

## 一、系统架构概览

你的系统有 **两条独立的使用路径**，测试用例的提问方式取决于走哪条路：

```
路径 A: dataagent（Java Web 应用，端口 8080）
  用户在浏览器输入自然语言 → Java 后端 → 调用 LLM 生成 SQL → 执行 → 展示结果

路径 B: hermes-agent（CLI/API）
  用户输入斜杠命令 → 加载 skill → LLM 按 skill 指引生成 SQL → 调用 MySQL 工具执行
```

---

## 二、路径 A：在 dataagent Web 系统中提问

dataagent 是运行在 `localhost:8080` 的 Java Web 应用（report_20250528.csv 中的测试就是这个系统）。
用户直接在 Web 页面输入**自然语言问题**，不需要任何前缀或特殊格式。

### 提问方式

直接输入问题文本，例如：

```
古运河有哪些测站
查询宝应水位站最近30天水位数据
2024年扬州城区降雨总量大概是多少？哪天降雨最大？
瘦西湖水质当前如何
查询当前超警戒水位的站点
未来24小时扬州市重点河道水位预测一下
查询所有闸站最新启闭状态
```

### 系统内部处理流程

```
用户输入 "古运河有哪些测站"
  │
  ▼
[domain-spec-v2.txt] 改写问题 → "在测站基础信息表(st_stbprp_b)中查找河流名称类似'古运河'，查询指标包含'测站编码、测站名称'"
  │
  ▼
[autoresearch-mix-sql-generator-system-v2.txt] 生成 SQL
  - 加载 schema_info（表结构）
  - 加载 domain（业务知识 → 来自 evidens.txt + skills/references/）
  - 加载 question_sql（few-shot → 来自 sqls.txt + skills/references/few_shots.md）
  - 加载 evidence（补充证据 → 来自 evidens.txt + skills/references/business_rules.md）
  │
  ▼
输出: SELECT stcd, stnm FROM sl323.st_stbprp_b WHERE rvnm LIKE '%古运河%' AND sttp = 'ZZ'
```

### 提问示例（按 skill 分类）

#### water-situation（实时水位）

| 问题 | 预期行为 |
|------|---------|
| 古运河有哪些测站 | 查询 st_stbprp_b，rvnm LIKE '%古运河%' |
| 宝应水位站最近30天水位数据 | 查询 st_river_r，关联 st_stbprp_b |
| 查询各水位站最新的水位值 | 每站取 MAX(tm) 对应的 z |
| 2024年古运河平均水位 | AVG(z) 按站分组 |
| 古运河水情 | 模糊查询，触发水位+流量 |
| 比较一下2023年和2024年古运河平均水位 | 跨年对比，YEAR 分组 |

#### rainfall（降雨）

| 问题 | 预期行为 |
|------|---------|
| 扬州城区今日降雨量 | stcd='58245', DATE(tm)=CURDATE() |
| 24年扬州城区哪天降雨最大 | GROUP BY DATE, ORDER BY SUM(drp) DESC LIMIT 1 |
| 未来2小时短临扬州市区雨量预测 | f_rnfl_h, UNITNAME='2', TYPE='2' |
| 扬州城区历史最大单日降雨量 | 全历史 GROUP BY DATE, ORDER BY SUM DESC LIMIT 1 |
| 最近一周各雨量站累计降雨量排名 | JOIN st_stbprp_b, SUM(drp) 按站 |

#### water-quality（水质）

| 问题 | 预期行为 |
|------|---------|
| 瘦西湖水质当前如何 | 最新 spt 的 dox/codmn/nh3n/tp/ph |
| 最近一个月瘦西湖水质变化趋势 | GROUP BY DATE(spt), AVG 各指标 |
| 帮我预测一下瘦西湖未来24小时水质 | slztk.st_mx_preset_r_shj_auto, type=103/104/105/128 |
| 京杭运河水质等级 | CASE WHEN 6 级标准评级 |

#### water-forecast（水位预测）

| 问题 | 预期行为 |
|------|---------|
| 未来24小时扬州市重点河道水位预测 | st_mx_preset_cal_r, type='1', 取最新 taskid |
| 预测瘦西湖未来24小时水位变化 | 指定站点预测 |
| 大模型对未来24小时河道水位预测 | 获取最新 taskid + 预测数据 |

#### gate-pump-operation（闸泵工况）

| 问题 | 预期行为 |
|------|---------|
| 查询所有闸站最新启闭状态 | st_gate_r, gtophgt > 0 = 开启 |
| 当前开启状态的泵站最新水情数据 | st_pump_r, omcn > 0 |
| 念四闸站上下游水位和过闸流量 | st_was_r, upz/dwz/tgtq |
| 泵站综合运行状态汇总 | GROUP BY 站名, SUM/CASE |

#### water-warning（水利预警）

| 问题 | 预期行为 |
|------|---------|
| 哪些站点超警戒水位 | st_river_r.z > st_rvfcch_b.WRZ |
| 防洪预警汇总 | 统计超警戒/超保证/正常站数 |
| 扬州市重点河道水位实时情况 | 5 个重点站 + 超警戒判断 |
| 水质低于Ⅳ类的站点 | wq_pcp_d, codmn>10 OR dox<3 OR nh3n>1.5 OR tp>0.3 |

---

## 三、路径 B：在 hermes-agent 中提问

hermes-agent 通过 **skill 斜杠命令** 激活水利领域知识。有三种方式：

### 方式 1：斜杠命令（推荐）

先输入 skill 命令，再输入问题。命令格式：`/<skill-name> <你的问题>`

```bash
# 激活水位查询 skill
/water-situation 古运河有哪些水位测站

# 激活降雨查询 skill
/rainfall 2024年扬州城区降雨总量大概是多少

# 激活水质查询 skill
/water-quality 瘦西湖水质当前如何

# 激活水位预测 skill
/water-forecast 未来24小时扬州市重点河道水位预测

# 激活闸泵工况 skill
/gate-pump-operation 查询所有闸站最新启闭状态

# 激活水利预警 skill
/water-warning 哪些站点超警戒水位
```

hermes 会自动：
1. 加载对应 skill 的 SKILL.md 作为指令上下文
2. 注入 references/ 目录下的 schema.md、business_rules.md、few_shots.md 作为知识
3. LLM 根据这些知识生成正确的 SQL
4. 如果配置了 MySQL 工具，自动执行 SQL 并返回结果

### 方式 2：预加载 skill 启动会话

```bash
# 启动时加载多个水利 skill
hermes --skills water-situation,water-warning,rainfall

# 启动后直接提问（不需要再输斜杠命令）
> 古运河有哪些水位测站
> 扬州城区降雨量
> 哪些站点超警戒水位
```

### 方式 3：让 LLM 自动选择 skill

如果 skill 已安装到 `~/.hermes/skills/water-resources/`，hermes 系统提示词中会包含 skill 索引：

```
Available Skills:
  water-situation: 实时水位查询...
  rainfall: 降雨查询...
  water-quality: 水质综合查询...
  water-forecast: 水位预测与模型计算...
  gate-pump-operation: 闸泵工况查询...
  water-warning: 水利预警...
```

当用户直接问水利问题时，LLM 会自动调用 `skill_view(name="water-situation")` 加载相关 skill：

```
> 古运河有哪些水位测站
（LLM 自动识别这是水位问题，加载 water-situation skill）
```

---

## 四、关键差异对比

| 维度 | dataagent (路径 A) | hermes-agent (路径 B) |
|------|-------------------|----------------------|
| **入口** | 浏览器 Web 页面 | CLI / API / 消息平台 |
| **提问格式** | 直接输入自然语言 | `/skill-name 问题` 或直接自然语言 |
| **知识加载** | Java 后端自动拼接 prompt 模板 | skill 斜杠命令触发加载 |
| **SQL 执行** | 后端连接 MySQL 执行 | hermes 调用 MySQL 工具执行 |
| **测试方法** | 在 8080 端口页面输入 | CLI 中输入 `/water-situation 问题` |

---

## 五、快速验证命令

### dataagent Web 测试

```bash
# 用 curl 模拟 Web 提问（具体 API 以实际接口为准）
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "古运河有哪些测站"}'
```

### hermes-agent CLI 测试

```bash
# 进入 hermes CLI
hermes

# 方式 1：斜杠命令
/water-situation 查询宝应水位站最近30天水位数据

# 方式 2：自动识别
古运河有哪些水位测站

# 方式 3：预加载后提问
hermes --skills water-situation
> 宝应水位站最近30天水位数据
```

---

## 六、测试用例文件位置

所有 98 条测试用例在：
```
/opt/git/hermes-agent/skills/water-resources/test_cases.md
```

每条用例包含：
- **自然语言问题**（可直接在 dataagent 或 hermes 中使用）
- **预期 SQL**（用于验证 LLM 输出是否正确）
- **难度标记**（L1/L2/L3）

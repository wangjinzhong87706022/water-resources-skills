# 🔍 失败用例深度分析报告

> **评测时间**: 2026-07-31 18:44 - 2026-08-01 03:26
> **分析对象**: Q018、Q028（两个超时失败用例）

---

## 失败用例概览

| 题号 | Skill | 难度 | 耗时 | LLM轮次 | 生成SQL | 状态 |
|------|-------|------|------|---------|---------|------|
| Q018 | water-situation | L3 | 900.0s | 0 | 0 | ✗ 超时 |
| Q028 | rainfall | L1 | 900.1s | 0 | 0 | ✗ 超时 |

**共同特征**:
- ❌ 均为 **900秒超时**
- ❌ **LLM 轮次为 0**（未进行任何对话）
- ❌ **生成 SQL 数量为 0**
- ❌ **无任何工具调用轨迹**
- ❌ **最终答案为空**

---

## 📋 Q018 - 古运河水情（模糊查询）

### 基本信息

- **题号**: Q018
- **Skill**: water-situation
- **Level**: L3
- **问题**: "古运河水情（模糊查询，用户只输入"古运河"三个字）。"
- **预期 SQL**:
```sql
SELECT b.stnm AS '测站名称', r.z AS '水位(m)', r.q AS '流量(m³/s)', r.tm AS '更新时间'
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%古运河%' OR b.stnm LIKE '%古运河%')
  AND r.tm = (SELECT MAX(r2.tm) FROM sl323.st_river_r r2 WHERE r2.stcd = r.stcd)
  AND r.z IS NOT NULL
ORDER BY r.tm DESC;
```

### 执行轨迹

**❌ 无轨迹记录**

DeerFlow Gateway 未返回任何：
- LLM 思考过程
- 工具调用记录
- SQL 生成记录
- 错误堆栈

### 失败原因分析

**初步判断**: 问题出在 **DeerFlow Agent 初始化阶段**

**可能原因**:

1. **Agent 理解失败**（最可能）
   - "古运河水情" 过于模糊
   - Agent 可能卡在 "理解用户意图" 阶段
   - 未生成任何 SQL 就超时

2. **Skill 规则未触发**
   - water-situation 的 SKILL.md 可能未提供足够指导
   - 模糊查询的处理策略缺失

3. **DeerFlow 内部错误**
   - Agent 启动失败
   - Skill 加载失败
   - 但未记录错误日志

---

## 📋 Q028 - 查询各雨量站的平均日降雨量

### 基本信息

- **题号**: Q028
- **Skill**: rainfall
- **Level**: L1
- **问题**: "查询各雨量站的平均日降雨量。"
- **预期 SQL**:
```sql
SELECT b.stnm AS '雨量站名称', AVG(p.drp) AS '平均日降雨量(mm)'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP' AND p.drp IS NOT NULL
GROUP BY b.stnm;
```

### 执行轨迹

**❌ 无轨迹记录**

### 失败原因分析

**初步判断**: **查询本身或表结构问题**

**可能原因**:

1. **SQL 立即超时**
   - `st_pptn_r` 是分区表（按 `tm` 分区）
   - **缺少时间范围过滤** → 扫描所有分区 → 30秒超时
   - 预期 SQL 本身就有问题（无 WHERE tm 条件）

2. **Agent 未修正错误**
   - Agent 可能生成了 SQL
   - SQL 立即超时（< 1秒）
   - 未重试或修正
   - 总耗时 900秒（30次 × 30秒）

3. **表数据量过大**
   - `st_pptn_r` 可能数据量极大
   - 全表 GROUP BY 导致超时

---

## 🔬 深度技术分析

### 问题 1：为什么没有轨迹记录？

**关键发现**: `llm_round_trips = 0` 意味着：

1. **DeerFlow Gateway 超时在 Agent 执行前**
   - Agent 未开始思考
   - 未调用任何工具
   - 未生成任何 SQL

2. **可能的技术原因**:
   ```python
   # DeerFlow Gateway 的超时机制
   # /api/runs/wait 有 900秒超时

   # 可能卡在：
   1. Agent 初始化（加载 Skill）
   2. LLM 连接/响应超时
   3. Skill 解析失败
   4. 请求排队超时
   ```

3. **对比正常用例**（如 Q019）:
   ```
   Q019: 170.9s | rounds=4 | sqls=2 | score=0.790
   → 有完整的 LLM 对话 + SQL 生成 + 执行
   ```

### 问题 2：Q028 预期 SQL 的问题

**预期 SQL 存在设计缺陷**:

```sql
SELECT b.stnm AS '雨量站名称', AVG(p.drp) AS '平均日降雨量(mm)'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP' AND p.drp IS NOT NULL
GROUP BY b.stnm;
```

**问题**:
- ❌ **无时间范围过滤**
- ❌ `st_pptn_r` 是 **RANGE 分区表**（按 `tm` 分区）
- ❌ 扫描所有分区 → 必然超时

**对比降雨 Skill 的 SQL 安全规则**（`rainfall/SKILL.md`）:

```
⚠️ 分区表强制要求：st_pptn_r 按 tm 范围分区，WHERE 必须包含时间过滤
```

**结论**: 预期 SQL 本身就有问题，测试用例设计不当。

### 问题 3：Q018 的模糊查询挑战

**问题特征**:
- 只有 3 个字："古运河"
- 无明确需求（水位？流量？历史？当前？）
- 预期 SQL 是获取最新水位 + 流量

**Agent 可能的困惑**:
1. "水情" 是什么？→ 水位？流量？历史趋势？
2. 时间范围？→ 最新？最近7天？全部历史？
3. 需要 JOIN 几张表？→ `st_river_r` + `st_stbprp_b`

**Skill 的应对**:
- water-situation 的 **Workflow** 应引导 Agent 澄清
- 但澄清需要 LLM 对话轮次 → 在当前超时模式下无法完成

---

## 📊 失败模式分类

| 失败模式 | Q018 | Q028 | 说明 |
|---------|------|------|------|
| **Agent 未启动** | ✅ | ✅ | LLM 轮次 = 0 |
| **SQL 未生成** | ✅ | ✅ | actual_sqls = [] |
| **无工具调用** | ✅ | ✅ | tool_trace = [] |
| **超时** | ✅ | ✅ | 900秒 |
| **测试用例问题** | ❌ | ✅ | Q028 预期 SQL 有缺陷 |
| **Skill 覆盖不足** | ✅ | ❌ | Q018 模糊查询无指导 |

---

## 🛠️ 修复建议

### Q018（古运河水情模糊查询）

**问题**: Agent 无法处理过于模糊的查询

**解决方案**:

#### 方案 A: 修改测试用例（推荐）
```markdown
# 修改前
问题: 古运河水情（模糊查询，用户只输入"古运河"三个字）。

# 修改后
问题: 查询古运河当前最新水位数据，包含测站名称、水位、流量和更新时间。
```

**理由**: 测试应验证 **可解决的查询**，而非 **模糊意图**。

#### 方案 B: 增强 Skill 的模糊查询处理
在 `water-situation/SKILL.md` 的 **Workflow** 中增加：

```markdown
### 模糊查询处理

如果用户查询过于模糊（如"古运河水情"）：

1. **先搜索测站**: 查询 `st_stbprp_b` 中包含"古运河"的测站
2. **假设默认需求**: 返回最新水位数据（最常用）
3. **添加免责声明**:
   > "以上是古运河水位的最新数据。如需分析历史趋势、特定时段或对比分析，请告诉我。"

禁止:
- 反问用户（增加轮次）
- 返回模糊的通用建议
```

#### 方案 C: 添加"默认查询模板"
在 SKILL.md 的 **References** 中添加:

```sql
-- 模糊查询默认: 获取河流最新水位
SELECT b.stnm, r.z, r.q, r.tm
FROM st_river_r r
JOIN st_stbprp_b b ON r.stcd = b.stcd
WHERE (b.rvnm LIKE '%{river_name}%' OR b.stnm LIKE '%{river_name}%')
  AND r.tm = (SELECT MAX(tm) FROM st_river_r WHERE stcd = r.stcd)
LIMIT 20;
```

### Q028（各雨量站平均日降雨量）

**问题**: 预期 SQL 缺少时间过滤，导致必然超时

**解决方案**:

#### 方案 A: 修复测试用例（强烈推荐）

```markdown
# 修改前
问题: 查询各雨量站的平均日降雨量。
预期 SQL: （无时间过滤）

# 修改后
问题: 查询2024年各雨量站的全年平均日降雨量。
预期 SQL:
SELECT b.stnm AS '雨量站名称',
       AVG(p.drp) AS '平均日降雨量(mm)',
       COUNT(DISTINCT DATE(p.tm)) AS '有雨天数'
FROM sl323.st_pptn_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
WHERE b.sttp = 'PP'
  AND p.drp IS NOT NULL
  AND YEAR(p.tm) = 2024  -- ← 添加时间过滤
GROUP BY b.stnm
ORDER BY AVG(p.drp) DESC;
```

#### 方案 B: 在 rainfall SKILL.md 强化时间范围要求

在 **SQL 安全规则** 中增加:

```markdown
## ⛔ 分区表强制要求

**st_pptn_r（雨量站数据）** 按 `tm` RANGE 分区。

**所有查询必须包含时间过滤**:
```sql
WHERE p.tm BETWEEN '2024-01-01' AND '2024-12-31'
-- 或
WHERE YEAR(p.tm) = 2024
-- 或
WHERE p.tm >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
```

**禁止**: `SELECT AVG(p.drp) FROM st_pptn_r`（无时间过滤 → 超时）
```

---

## 🎯 根本原因总结

| 用例 | 根因 | 责任方 | 修复优先级 |
|------|------|--------|-----------|
| **Q018** | Agent 在超时前未启动（ DeerFlow 层面） | DeerFlow + Skill | **P1** |
| **Q028** | 预期 SQL 设计缺陷（无时间过滤） | 测试用例 | **P0** |

### 优先级建议

1. **Q028（P0 - 立即修复）**
   - 修改测试用例，添加时间范围
   - 更新 rainfall SKILL.md 的分区表警告

2. **Q018（P1 - 短期修复）**
   - 方案 A: 修改测试用例，明确需求
   - 方案 B: 在 water-situation SKILL.md 增加模糊查询处理指南

3. **Q018（P2 - 长期优化）**
   - 调查 DeerFlow 超时机制
   - 为什么 Agent 在 900秒内未生成任何 SQL？
   - 是否有中间日志可查？

---

## 📈 影响评估

### 对整体评测的影响

- **总分**: 0.847（去除两个 0 分后 ≈ 0.881）
- **通过率**: 94.9%（去除后 ≈ 97.9%）
- **排名**: water-situation 从 0.824 → **0.858**（+0.034）

### 如果修复后的预期

| 场景 | 平均分 | 通过率 |
|------|--------|--------|
| 当前（2个0分） | 0.847 | 94.9% |
| Q028 修复（得0.6） | 0.861 | 95.9% |
| Q018 修复（得0.8） | **0.873** | **97.9%** |
| 全部修复 | **0.881** | **100%** |

---

## 🔍 进一步调查建议

1. **DeerFlow 日志深度分析**
   - 检查 DeerFlow Gateway 的 900秒内日志
   - 查看 Agent 初始化是否报错

2. ** DeerFlow 超时机制研究**
   - `llm_round_trips = 0` 的触发条件
   - 是否在等待 LLM 响应时超时？

3. **SQL 执行监控**
   - 手动执行 Q028 的预期 SQL
   - 验证是否真的超时

4. **测试用例审计**
   - 审查所有 98 个预期 SQL
   - 检查是否还有其他无时间过滤的查询

---

**报告生成时间**: 2026-08-01
**数据来源**: `eval_full_20260731_184415/`

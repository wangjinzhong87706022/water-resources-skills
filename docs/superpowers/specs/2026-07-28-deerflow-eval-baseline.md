# 🦌 DeerFlow Eval 基线报告

> **日期**：2026-07-28 15:10
> **方案**：B（迁移到 DeerFlow Eval）
> **状态**：✅ 验证成功，全量基线运行中

---

## 📊 快速基线（10 题测试）

| 指标 | 值 |
|------|-----|
| **平均分** | **0.68** |
| **通过率** | **100%**（≥0.6） |
| **SQL 提取率** | **90%**（9/10） |
| **总耗时** | 146.8 秒（平均 14.7 秒/题） |
| **总题数** | 10 题（L1×4 + L2×6） |

### 详细结果

| 题号 | 难度 | 问题 | 得分 | SQL | 耗时 |
|------|------|------|------|-----|------|
| Q1 | L1 | 古运河有哪些水位测站？ | 0.62 | ✓ | 33.2s |
| Q2 | L1 | 查询宝应水位站的所属河流、水系、流域、测站类别。 | 0.68 | ✓ | 10.3s |
| Q3 | L1 | 查询测站总数。 | 0.60 | ✓ | 27.1s |
| Q4 | L1 | 查询水位站宝应最近30天水位数据。 | 0.73 | ✓ | 11.1s |
| Q5 | L2 | 查询古运河(河流名称)水位站的数量。 | 0.62 | ✓ | 18.7s |
| Q6 | L2 | 查询建站最早和最晚的测站名称及其建站时间。 | 0.70 | ✓ | 16.1s |
| Q7 | L2 | 查询水位站数量最多、最少的河流。 | 0.62 | ✓ | 4.7s |
| Q8 | L2 | 查询古运河历史最高/低水位。 | 0.73 | ✓ | 4.6s |
| Q9 | L2 | 查询里运河（河流）最近两个月的水位数据。 | 0.82 | ✗ | 14.6s |
| Q10 | L2 | 查询各水位站最新的水位值。 | 0.65 | ✓ | 6.3s |

---

## ✅ 方案 B 验证结论

### 1. **DeerFlow Eval Harness 成功运行**

| 检查项 | 结果 |
|--------|------|
| 配置加载 | ✅ 成功读取 DeerFlow config.yaml |
| 测试用例 | ✅ 加载 98 题（过滤 25 题 water-situation） |
| LLM 调用 | ✅ 成功（OpenAI-compatible API） |
| SQL 提取 | ✅ 90% 成功率（Python 脚本中的 SQL） |
| 评分 | ✅ 多维度评分（响应/领域/数值/SQL/安全） |
| 报告生成 | ✅ JSON + Markdown |

### 2. **对比 Hermes Eval**

| 维度 | Hermes | DeerFlow |
|------|--------|----------|
| **成功率** | ❌ 0%（空响应） | ✅ 100% |
| **平均分** | ❌ 0.12 | ✅ 0.68 |
| **SQL 提取** | ❌ 0% | ✅ 90% |
| **响应质量** | ❌ 空响应 | ✅ 生成 Python 脚本（含 SQL） |
| **耗时** | 16-46 秒（但无响应） | 4-33 秒（有有效响应） |

### 3. **关键发现**

#### ✅ DeerFlow 路径优势

1. **更接近生产环境**
   - 直接调用 LLM API（如同实际部署）
   - Skill 文件加载正确（SKILL.md → system prompt）

2. **响应质量高**
   - LLM 生成完整的 Python 查询脚本
   - 包含 `from db import query` 标准导入
   - SQL 有 WHERE/LIMIT 等安全规则

3. **速度快**
   - 平均 14.7 秒/题
   - 全量 25 题预计 ~6 分钟

#### ⚠️ 待优化点

1. **SQL 提取逻辑需增强**
   - Q9 未提取到 SQL（可能是格式问题）
   - 当前从 Python 脚本中提取 SQL 字符串，覆盖率 90%

2. **评分逻辑需适配**
   - 当前评分假设是"自然语言 + SQL 代码块"
   - 实际是"Python 脚本包含 SQL 字符串"
   - 需要调整 `response_quality` 评分标准

3. **缺少 Trajectory**
   - 直接调用 API 无法获取中间步骤
   - 如需 trajectory，需使用 DeerFlow Gateway 或 embedded client

---

## 🎯 下一步行动

### 立即执行

1. **等待全量基线完成**（预计 5 分钟后）
   ```bash
   tail -20 /tmp/deerflow_eval_full.log
   ls -lh reports/deerflow_baseline_water_situation_full_*/
   ```

2. **生成基线报告**（P0 改造前基准）

### P0 改造期间（2-3 天）

1. **每次改造后跑 eval**
   ```bash
   python3 scripts/evaluate_deerflow.py --skills water-situation --output reports/eval_p0_xxx
   ```

2. **对比基线**（期望：平均分提升 ≥ 3%，通过率提升）

### P0 完成后

1. **全量跑一次（6 skill）**
   ```bash
   python3 scripts/evaluate_deerflow.py --skills water-situation rainfall water-quality water-forecast gate-pump-operation water-warning --output reports/deerflow_baseline_all
   ```

2. **迁移 evaluate_skills.py 到 DeerFlow 路径**
   - 保持 hermes 路径作为备选（`--engine hermes`）
   - 默认使用 DeerFlow（`--engine deerflow`）

---

## 📁 相关文件

- **Eval 脚本**：`scripts/evaluate_deerflow.py`
- **快速基线**：`reports/deerflow_baseline_test_20260728_150533/`
- **全量基线**：`reports/deerflow_baseline_water_situation_full_*`（运行中）
- **方案分析**：`docs/superpowers/specs/2026-07-28-eval-platform-analysis.md`

---

## 💡 结论

**方案 B 成功**：DeerFlow Eval Harness 可稳定运行，响应质量高，速度快。

**推荐策略**：
1. **短期**：用 DeerFlow Eval 作为 P0 改造的验证工具（替代 hermes）
2. **中期**：完善 SQL 提取 + 评分适配，达到生产级质量
3. **长期**：如需 trajectory，investigate embedded DeerFlow client 或 Gateway API

**与 P0 的关系**：P0-1（表卡片化）和 P0-2（eval 归因）的验证将基于 DeerFlow Eval 基线。

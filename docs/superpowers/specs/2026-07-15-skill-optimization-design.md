# Skill 优化设计方案

**日期**: 2026-07-15
**状态**: Draft → Pending Review
**目标**: 基于 water-situation 范本,优化其他 6 个数据/orchestration skills 的环境变量支持、多平台适配和 Validation Gate

---

## 一、现状诊断

### 1.1 行数对比

| Skill | 当前行数 | water-situation | 差距 |
|-------|---------|----------------|------|
| water-situation | 287 | 287 (范本) | - |
| water-fusion | 150 | - | -48% |
| water-visualization | 132 | - | -54% |
| rainfall | 89 | - | -69% |
| water-quality | 75 | - | -74% |
| gate-pump-operation | 78 | - | -73% |
| water-warning | 74 | - | -74% |
| water-forecast | 71 | - | -75% |

### 1.2 缺失功能矩阵

| Skill | 文件引用约定 | WATER_RESOURCES_ROOT | 标准导入片段 | Validation Gate |
|-------|------------|---------------------|-------------|-----------------|
| water-situation | ✅ | ✅ | ✅ | ✅ (6维) |
| rainfall | ❌ | ❌ | ❌ | ❌ |
| water-quality | ❌ | ❌ | ❌ | ❌ |
| water-forecast | ❌ | ❌ | ❌ | ❌ |
| gate-pump-operation | ❌ | ❌ | ❌ | ❌ |
| water-warning | ❌ | ❌ | ❌ | ❌ |
| water-fusion | ❌ | ❌ | ⚠️ 部分 | ⚠️ 简化版 |

---

## 二、优化策略

### 2.1 原则

**问题2 确认**: 根据每个 skill 的复杂度适当调整,不完全对齐 water-situation 的 287 行。

**目标行数范围**:
- 数据 skills (rainfall/water-quality/water-forecast/gate-pump-operation/water-warning): **100-150 行** (+40-80%)
- water-fusion: **180-220 行** (+20-47%)
- 可视化 skills (water-visualization/build-dashboard/create-viz): 保持现状,不需要 DB 导入

**不做过度设计**:
- 只有 water-situation 有 8 个 references/ (水体分类/高程基准/阈值验证等高频问题)
- 其他 skills 的 references/ 保持现有规模(1-2 个即可)
- Validation Gate 不盲目照搬 6 维,按业务定制

### 2.2 统一环境变量支持（所有 6 个 data/orchestration skills）

每个 skill 的 **Prerequisites** 章节添加:

#### 结构模板

```markdown
### 文件引用约定（双平台通用）

本 skill 通过「逻辑相对路径」引用共享资源,真实路径由**部署环境变量 `WATER_RESOURCES_ROOT`**（指向 skills/）派生：

| 引用 | 逻辑路径 | 运行时真实路径（两平台统一） |
|------|---------|---------------------------|
| 共享库 | `lib/db.py` | `$WATER_RESOURCES_ROOT/lib/db.py` |
| 共享文档 | `shared/db_connection.md` | `$WATER_RESOURCES_ROOT/shared/db_connection.md` |
| 共享规则 | `shared/sql_safety_rules.md` | `$WATER_RESOURCES_ROOT/shared/sql_safety_rules.md` |

> `WATER_RESOURCES_ROOT` 由部署层设置：DeerFlow 指向 `/mnt/skills`，Hermes 指向 `~/.hermes/skills/water-resources`，开发指向仓库 `…/skills`。

**标准导入片段**（生成查询代码时照抄，`__file__` 不可靠，勿用）：
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi
```
```

**为什么重要**:
- DeerFlow sandbox 环境会清洗 `*PASSWORD*` 变量,db.py 有文件回退逻辑,但路径必须正确
- Hermes 和本地开发路径不同,统一约定避免 `__file__` 硬编码

### 2.3 Validation Gate 定制方案

#### 2.3.1 rainfall (降雨量查询)

**检查维度** (3项):
- ✅ **数值范围**: 日降雨量 0~500mm,时段降雨 0~200mm
- ✅ **时间分布**: 月度总量不超过 800mm (扬州历史极值约 600mm/月)
- ✅ **测站数据完整性**: 缺测率 < 5%

**不检查**:
- ❌ 水体分类(降雨站无水体类型)
- ❌ 高程基准(降雨量无基准)

**目标行数**: 130 行 (+46%)

#### 2.3.2 water-quality (水质查询)

**检查维度** (4项):
- ✅ **指标范围**:
  - CODMn: 0~50 mg/L
  - DO: 0~20 mg/L
  - NH3N: 0~10 mg/L
  - TP: 0~5 mg/L
  - pH: 6~9
- ✅ **等级评定准确性**: 单因子评价法取最差等级
- ✅ **采样时间连续性**: 缺测率 < 10%
- ✅ **预测数据时效**: 水质预测任务距当前 < 24h

**不检查**:
- ❌ 水体分类(水质站已明确)
- ❌ 高程基准(水质无基准)

**目标行数**: 140 行 (+87%)

#### 2.3.3 water-forecast (水位预测)

**检查维度** (3项):
- ✅ **预测时效性**: 最新任务距当前 < 24h,否则提示"数据非实时"
- ✅ **预测值合理性**: 预测水位与实测水位偏差 < 2m (除非洪水涨水期)
- ✅ **任务状态**: 仅使用 stuts=1 的已完成任务

**不检查**:
- ❌ 水体分类(预测基于测站)
- ❌ 阈值对比(预测表无阈值)

**目标行数**: 120 行 (+69%)

#### 2.3.4 gate-pump-operation (闸泵工况)

**检查维度** (4项):
- ✅ **运行状态逻辑**:
  - 闸门: gtophgt > 0 → 已开启
  - 泵站: omcn > 0 → 有泵运行
  - switch=1 → 开, switch=0 → 关
- ✅ **分区表时间条件**: st_was_r/st_pump_r/st_pump_pa 必须带 WHERE tm 条件
- ✅ **测站类型正确性**: sttp='DD' (闸站), sttp='DP' (泵站)
- ✅ **数值范围**: 开度 0~100%, 流量 0~1000 m³/s

**不检查**:
- ❌ 水体分类(闸泵站无水体)
- ❌ 高程基准(闸泵高程单独管理)

**目标行数**: 130 行 (+67%)

#### 2.3.5 water-warning (水利预警)

**检查维度** (4项):
- ✅ **阈值对比准确性**:
  - 防洪: z > WRZ → 黄色, z > GRZ → 红色
  - 水质: 任一指标低于Ⅳ类触发预警
- ✅ **预警级别正确性**: 红/黄级别不能混淆
- ✅ **阈值数据存在性**: 查询 WRZ/GRZ 前必须验证(参考 water-situation 的 threshold_query_validation.md)
- ✅ **跨库 JOIN 大小写**: st_rvfcch_b.STCD 必须大写

**不检查**:
- ❌ 水体分类(预警基于测站)
- ❌ 高程基准(预警基于相对阈值)

**目标行数**: 130 行 (+76%)

#### 2.3.6 water-fusion (跨域融合)

**保持现有结构**,仅优化:
- ✅ 补充「文件引用约定」章节
- ✅ 补充 `WATER_RESOURCES_ROOT` 说明
- ✅ Validation Gate 保持现有 6 项检查,补充说明
- ✅ 增加「融合策略选择」的详细示例

**目标行数**: 200 行 (+33%)

---

## 三、实施计划

### Phase 1: 环境变量支持 (所有 6 个 skills)

**目标**: 统一添加「文件引用约定」+ 标准导入片段

**skills 清单**:
1. rainfall
2. water-quality
3. water-forecast
4. gate-pump-operation
5. water-warning
6. water-fusion

**每 skill 改动**:
- Prerequisites 章节末尾添加「文件引用约定」子章节
- 统一表格格式(参照 water-situation 第 39-56 行)
- **改动行数**: +10~15 行/skill

### Phase 2: Validation Gate 定制

**按业务优先级**:
1. **water-warning** (预警系统,影响最大) - 4 维检查
2. **water-quality** (水质民生) - 4 维检查
3. **gate-pump-operation** (调度核心) - 4 维检查
4. **rainfall** (降雨基础) - 3 维检查
5. **water-forecast** (预测辅助) - 3 维检查
6. **water-fusion** (融合编排) - 保持+优化

**每 Skill 改动**:
- Workflow 章节末尾添加「## Validation Gate」
- 每个检查维度包含:检查项 + 示例 + 常见错误
- **改动行数**: +20~40 行/skill

### Phase 3: 文档完善

- rainfall: 补充 `references/rainfall_range_validation.md`
- water-quality: 补充 `references/water_quality_rating.md` (6级标准详细说明)
- water-forecast: 补充 `references/forecast_freshness.md` (预测时效性判断)
- gate-pump-operation: 补充 `references/operation_status_logic.md` (运行状态判断规则)
- water-warning: 补充 `references/warning_level_mapping.md` (预警级别映射)

---

## 四、改动预估

| Skill | 当前行数 | 预估最终 | 增幅 | 关键改动 |
|-------|---------|---------|------|---------|
| water-situation | 287 | 287 | - | 范本,不变 |
| water-fusion | 150 | 200 | +33% | 环境变量 + Validation Gate 优化 |
| water-visualization | 132 | 132 | - | 可视化 skill,不需要 |
| rainfall | 89 | 130 | +46% | 环境变量 + Validation Gate |
| water-quality | 75 | 140 | +87% | 环境变量 + Validation Gate |
| gate-pump-operation | 78 | 130 | +67% | 环境变量 + Validation Gate |
| water-warning | 74 | 130 | +76% | 环境变量 + Validation Gate |
| water-forecast | 71 | 120 | +69% | 环境变量 + Validation Gate |
| build-dashboard | 60 | 60 | - | 可视化 skill,不需要 |
| create-viz | 89 | 89 | - | 可视化 skill,不需要 |
| data-context-extractor | 102 | 102 | - | 工具 skill,不需要 |

**总增量**: +295 行 (water-situation 287 行 → 其他 6 个 582 行)

---

## 五、不做的优化（保持现状）

1. **可视化 3 件套** (water-visualization/build-dashboard/create-viz): 无 DB 依赖,不需要环境变量
2. **data-context-extractor**: 工具型 skill,结构已合理
3. **public/ 下的 2 个通用 skills** (chart-visualization/data-analysis): 非水利业务,不混改
4. **water-situation 的 references/**: 8 个参考文档保持,不精简(高频问题确实需要)

---

## 六、成功标准

✅ **环境变量支持**:
- 所有 6 个 skills 的 Prerequisites 包含「文件引用约定」表格
- 明确说明 `WATER_RESOURCES_ROOT` 的 3 种路径(DeerFlow/Hermes/开发)
- 提供标准导入片段

✅ **Validation Gate**:
- 每个 data/orchestration skill 有至少 3 个检查维度
- 检查项与该 skill 的业务强相关(不盲目照搬)
- 包含常见错误示例

✅ **长度合理**:
- 数据 skills: 100~150 行
- water-fusion: < 220 行
- 不超过 water-situation 的 80% (除非业务复杂度确实更高)

---

## 七、下一步

**请确认**:
1. ✅ 优化策略是否符合预期?
2. ✅ Validation Gate 的检查维度设计是否合理?
3. ✅ Phase 1/2/3 的实施顺序是否可以?

确认后我开始实施,预计 15~20 分钟完成所有改动。

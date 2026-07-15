# Skill 优化设计方案（修订版）

**日期**: 2026-07-15
**状态**: Draft → Pending Review
**核心问题**: 其他 skills 是否真的需要增加行数？还是只是"对齐范本"的焦虑？

---

## 一、我的反思

我最初的设计犯了**形式主义错误**:
- ❌ 过早设定"目标行数"(100-150 行) → 为增加而增加
- ❌ 假设 Validation Gate 必须照搬 → 没验证 LLM 是否真的会执行
- ❌ 关注"完整性"而非"解决问题"

**正确的问题应该是**:
- ✅ 现有 skills 在实际使用中遇到了哪些**真实错误**？
- ✅ 哪些改动能**直接预防这些错误**？
- ✅ 最少需要增加多少内容？

---

## 二、真正的优化目标（按优先级）

### 🎯 目标 1: 环境变量支持（必须做）

**实际问题**: water-situation 的 Pitfalls 里反复强调的**高频错误**:
```
❌ "不要硬编码密码"
❌ "不要用 __file__ 定位 lib/"
❌ "密码在 sandbox 里不可见"
```

这些问题在 water-situation 真实发生过(commit history + eval failures)。

**其他 skills 现状**:
- 只写了"使用 `from db import query`"
- 没说路径怎么来
- 没说 __file__ 为什么不可靠
- 没说 DeerFlow sandbox 会清洗环境变量

**后果**:
- LLM 生成代码时手写 pymysql.connect() → 泄露密码 + 浪费 30+ 秒 token
- LLM 用 Path(__file__).parent → sandbox 里路径错误

**优化方案**（极简版，+10~12 行）:
```markdown
### 文件引用约定

本 skill 通过**环境变量 `WATER_RESOURCES_ROOT`**（指向 skills/）定位共享资源：

- `lib/db.py` → `$WATER_RESOURCES_ROOT/lib/db.py`
- `shared/db_connection.md` → `$WATER_RESOURCES_ROOT/shared/db_connection.md`

> `WATER_RESOURCES_ROOT` 由部署层设置：DeerFlow `/mnt/skills`，Hermes `~/.hermes/skills/water-resources`，开发指向仓库 `…/skills`。

**标准导入片段**（`__file__` 在 sandbox 暂存脚本中不可靠，勿用）：
\```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query, query_multi
\```
```

**预计总增量**: +60~72 行（6 个 skills × +10~12 行）

---

### ⚠️ 目标 2: Validation Gate（先试点再决定）

**我的担忧**: water-situation 的 Validation Gate 有 6 个检查维度，但：
1. LLM 会在实际查询时执行这些检查吗？(缺乏证据)
2. 还是只是"文档完整性"的装饰？

**需要验证的问题**:
- 查看 eval harness 的 `failed_trajectories.jsonl`
- 检查实际输出中是否有"水体分类错误""高程基准缺失""阈值硬编码"等问题

**如果确实有高频错误** → 针对性增加最小检查清单
**如果没有** → 保持现状,不增加

---

### ❌ 不做的优化

1. **盲目增加行数**: 不为"对齐范本"而增加
2. **照搬 6 维检查**: 不盲目复制 water-situation 的 Validation Gate
3. **为了完整性而完整性**: 每个 skill 的 Validation Gate 必须解决**实际问题**

---

## 三、实施计划

### Phase 1: 环境变量支持（立即执行）

**6 个 skills 各增加 +10~12 行**:
1. rainfall
2. water-quality
3. water-forecast
4. gate-pump-operation
5. water-warning
6. water-fusion

**每 skill 改动**:
- Prerequisites 章节末尾添加「文件引用约定」子章节
- **改动**: +10~12 行/skill
- **总增量**: +60~72 行

### Phase 2: Validation Gate 试点（先调研）

**行动**:
1. 查看 `skills/reports/eval_run/failed_trajectories.jsonl` (如果存在)
2. 统计最常见的错误类型
3. 对**真实发生频率最高的 1-2 个错误**设计最小检查清单
4. 只在 water-warning 和 water-quality 试点(预警/水质民生相关,错误影响大)

**如果 eval 数据不可用**: 询问用户"你在实际使用中有没有遇到过以下错误?"

---

## 四、改动预估（修订版）

| Skill | 当前行数 | 预估最终 | 增幅 | 关键改动 |
|-------|---------|---------|------|---------|
| water-situation | 287 | 287 | - | 范本,不变 |
| water-fusion | 150 | 165 | +10% | 环境变量支持 |
| water-visualization | 132 | 132 | - | 可视化 skill,不需要 |
| rainfall | 89 | 100 | +12% | 环境变量支持 |
| water-quality | 75 | 85 | +13% | 环境变量支持 |
| gate-pump-operation | 78 | 90 | +15% | 环境变量支持 |
| water-warning | 74 | 85 | +15% | 环境变量支持 |
| water-forecast | 71 | 80 | +13% | 环境变量支持 |
| build-dashboard | 60 | 60 | - | 可视化 skill,不需要 |
| create-viz | 89 | 89 | - | 可视化 skill,不需要 |
| data-context-extractor | 102 | 102 | - | 工具 skill,不需要 |

**总增量（仅 Phase 1）**: +80~94 行

**Phase 2（条件性）**: +20~60 行（仅在 Validation Gate 试点确认有必要后）

---

## 五、成功标准（修订）

✅ **Phase 1: 环境变量支持（必须）**:
- 6 个 skills 的 Prerequisites 包含极简版「文件引用约定」
- 说明 `WATER_RESOURCES_ROOT` 的 3 种路径
- 提供标准导入片段
- **总增量控制在 80~95 行以内**

✅ **Phase 2: Validation Gate（条件性）**:
- 只在 eval 数据显示有必要,或用户确认遇到过某类错误时才增加
- 每个检查维度必须解决**已发生的实际问题**
- 保持极简(1~2 个检查维度的最小清单)
- **如果增加,每 skill 不超过 15 行**

✅ **不做的优化**:
- 不为"对齐范本"而增加行数
- 不盲目照搬 Validation Gate
- 保持技能简洁可读

---

## 六、下一步

**请确认**:
1. ✅ 这个修订版的方向是否符合你的想法？（"解决问题 > 增加行数"）
2. ✅ Phase 1（环境变量支持）是否可以立即执行？
3. ✅ 关于 Validation Gate,你希望：
   - A) 先查看 eval harness 的错误数据再决定
   - B) 基于你的实际使用经验直接告诉我"哪些错误经常发生"
   - C) 保持现状,不做 Validation Gate

确认后我开始实施 Phase 1（预计 10 分钟完成所有 6 个 skills）。

# Eval 策略分析：全量 vs 局部验证

> **日期**：2026-07-28
> **背景**：P0-1 表知识卡片化完成（water-situation），需要验证效果

---

## 📊 选项对比

| 维度 | 全量验证（98 题） | 局部验证（water-situation 25 题） | 混合验证 |
|------|-----------------|--------------------------------|---------|
| **覆盖范围** | 6 个 skill | 1 个 skill | water-situation 全量 + 其他 5 题 |
| **耗时** | ~27 分钟 | ~10 分钟 | ~15 分钟 |
| **P0-1 目标验证** | ✅ 完整（但包含大量无关数据） | ✅ 直接命中 | ✅ 直接命中 |
| **意外影响检测** | ✅ 完整（但 P0-1 理论上不影响其他 skill） | ⚠️ 无法检测 | ⚠️ 只能抽样检测 |
| **数据完整性** | ✅ 基线对比完整 | ❌ 缺少其他 skill 数据 | 🟡 部分完整 |

---

## 🎯 推荐策略

### **选项 C：混合验证（最优）**

**理由**：

1. **P0-1 只改了 water-situation**
   - 其他 5 个 skill 文件未修改
   - 理论上不会影响其他 skill 的评分
   - **无需全量验证**

2. **验证目标明确**
   - P0-1 的核心目标：water-situation 平均分从 0.68 → ≥ 0.75
   - Q2/Q15/Q19 从低分（< 0.6）→ 通过（≥ 0.6）
   - **只需看 water-situation 数据**

3. **混合验证兼顾**
   - ✅ **water-situation 全量 25 题**：验证 P0-1 改造效果
   - ✅ **其他 skill 各 3 题**：确认无意外影响（抽样）
   - ⏱️ **总耗时 ~15 分钟**（比全量快 12 分钟）

---

## 📋 验证方案

### **Phase 1：water-situation 全量验证（核心）**

```bash
python3 scripts/evaluate_deerflow.py \
  --skills water-situation \
  --output reports/eval_p0_1_water_situation
```

**预期结果**：
- 平均分：0.68 → **≥ 0.75**（+10%+）
- 低分用例：3 题（Q2/Q15/Q19）→ **≤ 1 题**
- Q2 得分：0.38 → **≥ 0.6**
- Q15 得分：0.53 → **≥ 0.7**
- Q19 得分：0.58 → **≥ 0.7**

### **Phase 2：其他 skill 抽样验证（可选）**

```bash
python3 scripts/evaluate_deerflow.py \
  --skills rainfall,water-quality,water-forecast,gate-pump-operation,water-warning \
  --max-cases 3 \
  --output reports/eval_p0_1_sampling
```

**目的**：确认 P0-1 对其他 skill 无负面影响（理论上不可能，但验证更安全）

---

## ⏱️ 时间估算

| 阶段 | 题数 | 预计耗时 |
|------|------|---------|
| water-situation 全量 | 25 | ~10 分钟 |
| 其他 5 skill 抽样（各 3 题） | 15 | ~5 分钟 |
| **总计** | **40** | **~15 分钟** |

**对比**：全量 98 题需 ~27 分钟，节省 **12 分钟（44%）**

---

## 🎯 决策建议

### ✅ 推荐：混合验证

**如果**：
- P0-1 只改了 water-situation
- 验证目标是确认 water-situation 提升
- 时间宝贵（15 分钟 vs 27 分钟）

**那么**：
1. **先跑 water-situation 全量（25 题）**
2. **如果结果达标** → 可跳过其他 skill 抽样
3. **如果结果不达标** → 再跑其他 skill 排查问题

### ❌ 不推荐：全量验证

**原因**：
- 27 分钟等待时间长
- 大部分数据（73 题）与 P0-1 无关
- 信息密度低（10 分钟获得关键信息 vs 27 分钟）

### ⚠️ 可选：极简验证

**如果时间极度紧张**：
- 只跑 water-situation 的 **低分用例（Q2/Q15/Q19）**
- 耗时 ~2 分钟
- 直接验证 P0-1 是否解决核心问题

---

## 📊 验证命令

### 方案 A：混合验证（推荐）

```bash
# Step 1：water-situation 全量（核心）
python3 scripts/evaluate_deerflow.py \
  --skills water-situation \
  --output reports/eval_p0_1_ws_full

# Step 2：其他 skill 抽样（确认无影响）
python3 scripts/evaluate_deerflow.py \
  --skills rainfall,water-quality,water-forecast,gate-pump-operation,water-warning \
  --max-cases 3 \
  --output reports/eval_p0_1_sampling
```

### 方案 B：仅 water-situation（快速）

```bash
python3 scripts/evaluate_deerflow.py \
  --skills water-situation \
  --output reports/eval_p0_1_ws_only
```

### 方案 C：仅低分用例（极速）

```bash
# 手动验证 Q2/Q15/Q19（需要修改脚本支持题号过滤）
# 或直接查看基线报告中的这 3 题，对比预期改进
```

---

## 💡 结论

**推荐方案 A（混合验证）**：

1. ✅ **water-situation 全量**：验证 P0-1 核心目标
2. ✅ **其他 skill 抽样**：确认无意外影响
3. ⏱️ **总耗时 ~15 分钟**：比全量快 44%
4. 📊 **数据完整**：覆盖核心验证目标 + 安全校验

**如果追求极致速度** → 方案 B（仅 water-situation，10 分钟）
**如果需要 100% 置信度** → 全量验证（27 分钟）

**您的选择**：
- **A：混合验证**（推荐）
- **B：仅 water-situation**
- **C：全量验证**
- **D：仅低分用例（Q2/Q15/Q19）**

# 阈值查询验证方法

> **适用范围**：`water-situation` skill 及 `water-warning` skill 中涉及警戒水位、保证水位、蓄水位等阈值的场景
> **数据来源**：`sl323.st_rvfcch_b`（防洪指标表）
> **重要警告**：该表**数据质量极差**，阈值字段大量缺失，使用前必须验证

---

## 1. 数据质量实况（2026-07-13 实测）

### 1.1 全表统计

| 字段 | 总记录数 | 非空记录数 | 非空率 | 状态 |
|------|---------|-----------|-------|------|
| WRZ（警戒水位） | 231 | 176 | **76%** | ⚠️ 部分有值 |
| GRZ（保证水位） | 231 | **0** | **0%** | ❌ **全部为空** |
| WRQ（警戒流量） | 231 | 部分 | 待统计 | ⚠️ |
| GRQ（保证流量） | 231 | 部分 | 待统计 | ⚠️ |
| LDKEL/RDKEL（岸高程） | 231 | ~20 | ~9% | ❌ 基本为空 |

**关键发现**：
- ❌ **GRZ（保证水位）全表 0% 有值**，该字段**完全不可用**
- ⚠️ **WRZ（警戒水位）仅 76% 有值**，且主要集中在**闸泵站**（站码以 `HP` 开头）
- ❌ **水位站（ZZ）/水文站（ZQ）的阈值字段基本全部为空**

### 1.2 三水域代表站实测

| 测站 | 水体 | WRZ（警戒水位）| GRZ（保证水位）| 状态 |
|------|------|--------------|--------------|------|
| 蒋坝 | 洪泽湖 | **NULL** | **NULL** | ❌ 全部缺失 |
| 大通(二) | 长江 | **NULL** | **NULL** | ❌ 全部缺失 |
| 宝应 | 里运河 | **NULL** | **NULL** | ❌ 全部缺失 |

**结论**：三水域代表站的阈值数据**全部缺失**，数据库中**不存在**洪泽湖警戒水位 14.35m、长江警戒水位等数值。

---

## 2. 查询前验证流程（强制）

### 2.1 三步验证法

在查询任何阈值（WRZ/GRZ/蓄水位等）之前，**必须**执行以下验证：

#### Step 1：验证表中有数据

```sql
-- 验证该测站是否有阈值记录
SELECT COUNT(*) as cnt
FROM sl323.st_rvfcch_b
WHERE STCD = '目标测站编码'
  AND (WRZ IS NOT NULL OR GRZ IS NOT NULL)
```

**判断逻辑**：
```python
result = query(sql)
if result[0]['cnt'] == 0:
    # ❌ 无数据，跳过阈值查询
    return "⚠️ 该站阈值数据缺失，无法判断超警戒/超保证状态"
```

#### Step 2：验证字段值非空

即使 Step 1 有记录，仍需验证具体字段值：

```sql
SELECT STCD, WRZ, GRZ
FROM sl323.st_rvfcch_b
WHERE STCD = '目标测站编码'
```

**判断逻辑**：
```python
row = query(sql)[0]
if row['WRZ'] is None:
    # ❌ 警戒水位字段为空
    warn("⚠️ 警戒水位数据缺失（WRZ=NULL）")
if row['GRZ'] is None:
    # ❌ 保证水位字段为空
    warn("⚠️ 保证水位数据缺失（GRZ=NULL）")
```

#### Step 3：验证数值合理性

如果字段有值，需检查合理性：

```python
if row['WRZ'] is not None:
    if not (0 < row['WRZ'] < 20):
        # ❌ 水位超出合理范围（0~20m）
        warn(f"⚠️ 警戒水位异常：{row['WRZ']}m（超出合理范围）")
```

### 2.2 完整验证示例

```python
def validate_threshold(stcd: str) -> dict:
    """验证测站阈值数据是否存在且合理"""

    # Step 1：验证表中有记录
    sql_cnt = f"""
    SELECT COUNT(*) as cnt
    FROM sl323.st_rvfcch_b
    WHERE STCD = '{stcd}'
      AND (WRZ IS NOT NULL OR GRZ IS NOT NULL)
    """
    cnt_result = query(sql_cnt)
    if cnt_result[0]['cnt'] == 0:
        return {
            'valid': False,
            'message': f'⚠️ {stcd} 阈值数据全部缺失（WRZ/GRZ 均为空）'
        }

    # Step 2：验证字段值
    sql_val = f"""
    SELECT STCD, WRZ, GRZ
    FROM sl323.st_rvfcch_b
    WHERE STCD = '{stcd}'
    """
    val_result = query(sql_val)
    row = val_result[0]

    issues = []
    if row['WRZ'] is None:
        issues.append('WRZ（警戒水位）为空')
    if row['GRZ'] is None:
        issues.append('GRZ（保证水位）为空')

    # Step 3：验证数值合理性
    if row['WRZ'] is not None and (row['WRZ'] < 0 or row['WRZ'] > 20):
        issues.append(f"WRZ 异常值：{row['WRZ']}m")
    if row['GRZ'] is not None and (row['GRZ'] < 0 or row['GRZ'] > 20):
        issues.append(f"GRZ 异常值：{row['GRZ']}m")

    return {
        'valid': len(issues) == 0,
        'message': '✅ 阈值数据完整' if not issues else '⚠️ ' + '；'.join(issues),
        'WRZ': row['WRZ'],
        'GRZ': row['GRZ']
    }
```

---

## 3. 缺失时的处理规范

### 3.1 不要硬编码阈值

❌ **错误做法**：
```python
# 硬编码洪泽湖警戒水位
hongze_wrz = 14.35  # 来自外部文件
```

**问题**：无法证明此数值与数据库一致，数据源不透明。

✅ **正确做法**：
```python
# 先从数据库查询，验证存在后再使用
threshold = query_threshold('蒋坝站STCD')
if threshold['WRZ'] is None:
    return "⚠️ 蒋坝站警戒水位数据缺失，无法判断超警戒状态"
else:
    compare_with_threshold(current_z, threshold['WRZ'])
```

### 3.2 缺失时的用户告知

当阈值数据缺失时，按以下模板告知用户：

```markdown
⚠️ **阈值数据缺失说明**

- 测站：蒋坝（洪泽湖）
- 缺失字段：WRZ（警戒水位）= NULL，GRZ（保证水位）= NULL
- 数据来源：sl323.st_rvfcch_b
- 影响：无法判断当前水位是否超警戒/超保证

**建议**：
1. 对接省防指调度文件，获取洪泽湖最新防洪指标
2. 或使用历史同期水位作为参考（如近5年同期最高水位）
```

### 3.3 历史极值替代方案

当阈值缺失时，可提供**历史极值**作为参考：

```sql
-- 查询历史最高水位（非阈值，但可作为参考）
SELECT MAX(z) as historical_max,
       PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY z) as p99,
       COUNT(*) as n
FROM sl323.st_river_r r
JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm LIKE '%蒋坝%'
  AND r.tm >= DATE_SUB(CURDATE(), INTERVAL 10 YEAR)
  AND r.z IS NOT NULL
```

**输出说明**：
```markdown
📊 **历史水位参考**（蒋坝站，近10年）
- 历史最高水位：14.25m（2020-07-21）
- p99 水位：13.85m
- ⚠️ 此数据**非官方阈值**，仅供参考
```

---

## 4. 全库阈值数据质量报告

### 4.1 闸泵站 vs 水位站/水文站对比

| 测站类型 | 有阈值记录比例 | 典型基准 |
|---------|--------------|---------|
| 闸泵站（HP 开头） | **较高**（部分有值） | 废黄河口 |
| 水位站（ZZ） | **极低**（基本为空） | 待确认 |
| 水文站（ZQ） | **极低**（基本为空） | 待确认 |

**结论**：
- 闸泵站（HP 编码）的阈值数据相对完整
- 水位站（ZZ）和水文站（ZQ）的阈值字段**基本全部为空**
- **不要假设所有测站都有阈值数据**

### 4.2 数据缺失的根本原因

可能原因（待确认）：
1. **表结构设计问题**：`st_rvfcch_b` 中水位站/水文站的阈值字段未填充
2. **数据来源问题**：阈值数据可能存储在其他系统（如省防指调度系统）
3. **历史遗留**：该表可能主要服务于闸泵站，水位站数据未迁移

---

## 5. 使用规则

### 5.1 强制规则（违反会导致错误结论）

1. **查询前必须验证**：任何阈值使用前，必须执行 §2 的三步验证法
2. **不硬编码阈值**：所有阈值必须来自数据库查询结果
3. **缺失时明确告知**：阈值字段为空时，**不能猜测或估算**，必须告知用户"数据缺失"
4. **标注数据源**：即使有值，也需说明"数据来源：sl323.st_rvfcch_b"

### 5.2 推荐做法

1. **优先使用闸泵站数据**：HP 编码的闸泵站阈值数据相对完整
2. **水位站/水文站提供历史极值**：阈值缺失时，提供历史最高水位作为参考
3. **建议补充外部数据源**：如需完整的防洪指标，建议对接省防指调度文件

---

## 6. 案例教训

### 6.1 案例中的错误

**案例声称**：
- "洪泽湖警戒水位 14.35m"
- "正常蓄水位 12.81m"
- "规划蓄水位 13.31m"

**数据库实测**：
- ❌ 蒋坝站 WRZ = NULL（无警戒水位）
- ❌ GRZ 全表 0% 有值（无保证水位）
- ❌ 无"蓄水位"字段（`st_rvfcch_b` 中无此类字段）
- ❌ 三数值**全部无法在本库证实**

### 6.2 不能引用的外部数据

如遇以下情况，**不能直接引用**到报告中：

| 数值 | 来源 | 可用性 |
|------|------|--------|
| 14.35m | 案例引用 | ❌ **无法证实**（数据库无此数据） |
| 12.81m | 案例引用 | ❌ **无法证实** |
| 13.31m | 案例引用 | ❌ **无法证实** |
| 0.19m（基准换算） | 案例引用 | ⚠️ **常识但本库无实测支撑** |

**正确做法**：
> "本库中蒋坝站阈值数据缺失，无法引用 14.35m 等数值。如需防洪评估，建议对接省防指调度文件。"

---

## 7. 更新日志

| 日期 | 更新内容 | 依据 |
|------|---------|------|
| 2026-07-13 | 初始版本，基于数据库实测建立阈值验证流程 | `knowledge_verification_report.md` |

---

**维护说明**：本知识库基于 `sl323.st_rvfcch_b` 表实测数据建立。如该表数据质量改善（如 GRZ 字段填充），请更新 §1 的统计数字。

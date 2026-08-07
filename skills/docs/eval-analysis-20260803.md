# DeerFlow Gateway 全量评估分析(2026-08-03)

> **评估时间**:2026-08-03 15:11 启动 → 2026-08-04 00:09 完成(约 8.8h)
> **模式**:Gateway `/api/runs/wait`(真实 agent 全栈)| Gateway `localhost:8001`
> **数据源**:`reports/eval_gateway_full_20260803_151150/gateway_eval_all_20260804_000908.json`
> **SKILL 版本**:含 commit `297b330`(fix: 间歇超时兜底 + golden SQL 对齐);`water-forecast/SKILL.md` 另有 1 行未提交改动

## 1. 总体结果

| 指标 | 值 |
|---|---|
| 用例数 | 98(全量) |
| 平均分 | **0.864** |
| 通过率(≥0.6) | **96.9%**(95/98) |
| 全部完成 | 是(无超时/崩溃) |
| 平均 LLM 轮次 | 8.9(max **29**) |
| 平均 SQL 数 | 7.1(max **51**) |
| 总耗时 | 8.8h |

## 2. 基线对比(7/31 v2)

> ⚠️ v2 只跑了前 55 题,逐题对比**仅覆盖 Q001–Q055**;Q056–Q098 无历史基线。

| 指标 | 7/31 v2(55题) | 8/3 本次(98题) | Δ |
|---|---|---|---|
| 均分 | 0.850 | 0.864 | **+0.013** |
| 通过率(≥0.6) | 96.4% | 96.9% | +0.5pp |
| 逐题(前55) | — | 上升 **23** / 下降 **8** / 持平 24 | 净 +15 |

**回退最严重(关注)**:

| Q# | Skill | 7/31 | 8/3 | Δ |
|---|---|---|---|---|
| Q014 | water-situation | 0.933 | 0.663 | **-0.270** |
| Q028 | rainfall | 0.800 | 0.534 | **-0.266** |
| Q030 | rainfall | 0.850 | 0.600 | **-0.250** |
| Q045 | water-quality | 1.000 | 0.750 | **-0.250** |
| Q047 | water-quality | 0.950 | 0.750 | **-0.200** |

**进步最大**:Q010(+0.374)、Q007(+0.300)、Q044(+0.250)、Q009(+0.224)、Q004/Q046/Q053/Q055(+0.210)。

## 3. 评分维度(短板定位)

| 维度 | 均值 | 判断 |
|---|---|---|
| has_valid_response | 1.000 | 满 |
| sql_generated | 1.000 | 满 |
| **sql_replay_ok** | **0.857** | **14 题重放失败** |
| **result_quality** | **0.725** | **最大短板** |
| trace_sanity | 0.816 | 多题 0.5(轨迹打转) |

修复杠杆集中在 `sql_replay_ok` + `result_quality`——二者高度重叠:都是"最终那条 SQL 拿不到/拿不对数据"。

**按 skill**:`water-forecast` 均分最低 0.768(6 skill 倒一,但无 <0.7 题,是系统性天花板而非个别失败);`water-warning` mean 0.831 但有 3 题 <0.7(min 0.490)。

**按 level**:L1=0.867、L2=0.828、L3=0.875。L2 略低(受 Q028/Q030/Q089/Q089 拖累)。

## 4. 低分 Case 根因(三类)

### ① 占位符泄漏(致命,可根治)— Q098 / Q014 / Q094

最终提交的 SQL 残留未填值的模板变量,MySQL 无法执行 → `sql_replay_ok=0`:

- Q098(0.490): `WHERE stcd = '{stcd}' AND z > {wrz}`
- Q014(0.663): `WHERE b.stcd IN ({stcd_list})`
- Q094(0.695): `WHERE STCD IN ({stcd_list})`(答案本身正确 result_q=0.984,纯粹被末条 SQL 拖累)

**根因(已验证)**:`water-situation/SKILL.md:135-138` 存在一个"❌ 错误 vs ✅ 正确"对照块,**❌ 反例里直接写了带 `{stcd}`/`{dt}` 的 SQL 代码**。LLM 从 SKILL.md 抓取 SQL 片段时分不清"反例"与"模板",直接照抄(DeerFlow 仅加载 SKILL.md,该反例是其可见的少数 SQL 范式之一)。同文件的"禁止占位符"禁令被这个反例代码块削弱。

### ② 无效探测 SQL — Q089(0.580)

最终 SQL 为 `SELECT 1 FROM sl323.st_river_r r`——LLM 打转 9 轮未收敛出有效查询。trace_sanity=0.5。

### ③ 聚合口径 + 分区表无 tm 范围 — Q028(0.534)/ Q030(0.600)

SQL 合法,但 `st_pptn_r` 是 RANGE 分区表、WHERE 无 `tm` 范围 → replay 扫全分区被拒/超时 → `sql_replay_ok=0`;叠加"平均日降雨量""各区域累计"算法与 golden 口径不一致 → result_q 低。

## 5. 系统性问题

### 5.1 0-rows 探测循环(性能 + trace 双杀手)
日志海量重复 `Query returned 0 rows` → `Check get_date_range(table) for time coverage`。LLM 默认 `NOW()/CURDATE()` 查历史/预测数据,空结果后靠 hint 反复重试,直接造成:
- 高轮次:Q014=29、Q094=29、Q046=28、Q057=28、Q050=27、Q053=27、Q049=25
- 高 SQL 数:Q094=**51**
- 8.8h 总耗时、trace_sanity 普遍掉到 0.5

### 5.2 water-forecast 时间窗天花板
Q057–Q069 集中卡在 0.74。预测表 `slztk.st_mx_preset_cal_r` 数据在特定 taskid 时间窗,LLM 用 `NOW() BETWEEN...` 永远查不到。SKILL.md:68 已有"禁止 NOW() BETWEEN、锚定 taskid 时间"的禁令,但 LLM 未稳定遵守。

### 5.3 eval 对"数据缺失优雅降级"不友好
Q098 的 `GRZ(保证水位)` 字段**真实全 NULL**——agent 已识别缺失并降级给出 WRZ 替代方案(行为正确),却被 `replay_ok=0 + result_q=0.3` 重罚。属评分机制问题,非 skill 问题。

## 6. 改进建议(按杠杆排序)

| 优先级 | 动作 | 预期救回 |
|---|---|---|
| **P0** | 删除 SKILL.md 内联 SQL 里**所有** `{...}` 占位符代码块(尤其 water-situation:135-138 的 ❌ 反例),改成纯文字描述,只留 ✅ 正例;给 **water-forecast 补独立「禁占位符」强禁令** | Q098/Q014/Q094 直接回升 |
| **P0** | water-forecast 预测表时间窗:用**最新 taskid 锚定**,禁止 `NOW() BETWEEN`(:68 已有,需提升遵守率) | Q057–Q069 整体抬升 |
| **P1** | 分区表/预测表时间覆盖**前置**:SKILL 直接内嵌各表 `MAX(tm)`/数据窗,把"0-rows 后才 hint"改为"首次查询前就知道" | 砍轮次/耗时,提 trace_sanity |
| **P2** | Q028/Q030 golden 聚合口径对齐 + 强制分区表 WHERE 带 tm | 修 2 处回退 |
| **评估侧** | eval 对"数据缺失优雅降级"给部分分(Q098 类) | 评分公平性 |

---

## 附录 A:<0.7 case 清单

| Q# | Skill | Level | Score | 轮次 | SQL数 | 类别 |
|---|---|---|---|---|---|---|
| Q098 | water-warning | L3 | 0.490 | 11 | 14 | ① 占位符 + 数据缺失 |
| Q028 | rainfall | L1 | 0.534 | 4 | 1 | ③ 口径+无tm |
| Q089 | water-warning | L2 | 0.580 | 9 | 7 | ② 无效探测 |
| Q030 | rainfall | L2 | 0.600 | 6 | 3 | ③ 口径+无tm |
| Q014 | water-situation | L3 | 0.663 | 29 | 26 | ① 占位符(打转) |
| Q094 | water-warning | L3 | 0.695 | 29 | 51 | ① 占位符(末条) |

## 附录 B:sql_replay_ok=0 的 14 题

Q009、Q014、Q021、Q024、Q028、Q030、Q045、Q047、Q074、Q080、Q087、Q089、Q094、Q098

> 其中 Q098/Q014/Q094 为占位符泄漏(本次 P0 修复对象);Q028/Q030 为分区表无 tm 范围;其余多为末条 SQL 非主查询的探测/兜底语句。

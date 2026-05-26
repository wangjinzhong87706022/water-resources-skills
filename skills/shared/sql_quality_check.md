# SQL 质量审查流程

> 所有水利 skill 通用质量审查。在生成 SQL 后、返回结果给用户前执行。

## Step 1: 表名列名校验

- 检查 SQL 中的表名是否在当前 skill 的 `references/schema.md` 中定义
- 检查列名是否在 schema.md 的列清单中（防止拼写错误）
- 特别注意大小写敏感的列名：
  - `st_rvfcch_b.STCD`（大写）vs `st_river_r.stcd`（小写）
  - `st_mx_preset_cal_r.type` 是 varchar，`st_mx_preset_r_shj_auto.type` 是 int

## Step 2: 时间条件完整性

- 所有查询**必须包含时间范围条件**
- "最新/当前/实时" → 取 MAX(tm) 或 ORDER BY tm DESC LIMIT 1
- "最近N天" → `tm >= DATE_SUB(CURDATE(), INTERVAL N DAY)`
- "某天左右" → 前后 3 天范围
- "本月/当月" → `tm >= DATE_FORMAT(CURDATE(), '%Y-%m-01')`
- 预测表：先查最新任务时间，若距今过久需告知用户

## Step 3: 空结果处理

如果执行结果为空，按以下策略**自动重试一次**：

1. **扩大时间范围** — 如 "最近3天" → "最近10天"
2. **模糊匹配名称** — 如 `= '古运河'` → `LIKE '%古运河%'`
3. **检查河流别名** — 参照各 skill 的 `business_rules.md` 中的重点河道映射
4. **检查测站类型** — 确认 sttp 过滤条件是否正确

## Step 4: 结果合理性检查

返回结果前，快速验证数值合理性：

| 数据类型 | 合理范围 | 异常处理 |
|---------|---------|---------|
| 水位 (z/rz) | -1 ~ 20 m | 超出范围提示单位可能有误 |
| 降雨量 (drp/dyp) | 0 ~ 500 mm | 单日 > 200mm 需标注"极端降雨" |
| 流量 (q) | 0 ~ 10000 m³/s | 负值提示数据异常 |
| 水质 CODMn | 0 ~ 50 mg/L | > 30 需标注"严重超标" |
| 水质 DO | 0 ~ 20 mg/L | < 2 需标注"缺氧" |
| 水位保留两位小数 | ROUND(z, 2) | 所有水位输出必须保留2位 |

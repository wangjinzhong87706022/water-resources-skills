# 水位预测 Few-Shot 示例

> ⚠️ **预报时间窗必须锚任务 tm，禁锚 NOW()**——最新任务可能很旧，NOW() 窗口与预报 tm 无交集必返 0 行。type/stuts 等 char 字段必须带引号（`type = '1'`、`stuts = '1'`）。

> 来源: /home/scada/dataagent/domains/sqls.txt 原始 Question-SQL 对

### Q: 查询未来24小时扬州市重点河道水位

```sql
SELECT taskid, r.stcd AS '测站编码', REPLACE(b.stnm, '计算水位', '') AS '测站名称',
       tm AS '预报时间', vals AS '预报值'
FROM slztk.st_mx_preset_cal_r r
INNER JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）',
                  '七里河水位站（东花园路）', '赵家支沟水文站（赵家河路）', '瘦西湖水位站')
  -- 时间窗锚定该任务自身的预报起点（MIN(tm)），取其后 24 小时；禁止锚 NOW()
  AND tm < DATE_ADD((SELECT MIN(tm) FROM slztk.st_mx_preset_cal_r
                     WHERE taskid = (SELECT taskid FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1)
                       AND type = '1'), INTERVAL 24 HOUR)
  AND type = '1'
  AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1)
ORDER BY tm;
```

**注意:**
- st_mx_preset_cal_r 在 **slztk** 库，st_stbprp_b 在 **sl323** 库
- type 是 **varchar(5)**，用 `type = '1'`（不是 `type = 1`）
- 跨库查询需带库名前缀
- **禁止 `tm >= NOW() AND tm <= DATE_ADD(NOW(), INTERVAL 24 HOUR)`**：最新任务可能很旧，NOW() 窗口与预报 tm 无交集必返 0 行。若一个任务只覆盖约 24 小时预报，也可直接去掉时间窗、仅按 taskid 取该任务全部预报时段，并在答复中注明任务时间

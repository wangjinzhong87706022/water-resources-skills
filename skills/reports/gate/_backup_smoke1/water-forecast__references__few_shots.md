# 水位预测 Few-Shot 示例

> 来源: /home/scada/dataagent/domains/sqls.txt 原始 Question-SQL 对

### Q: 查询未来24小时扬州市重点河道水位

```sql
SELECT taskid, r.stcd AS '测站编码', REPLACE(b.stnm, '计算水位', '') AS '测站名称',
       tm AS '预报时间', vals AS '预报值'
FROM slztk.st_mx_preset_cal_r r
INNER JOIN sl323.st_stbprp_b b ON r.stcd = b.stcd
WHERE b.stnm IN ('古运河水位站（新城河口）', '新城河水文站（兴城西路北）',
                  '七里河水位站（东花园路）', '赵家支沟水文站（赵家河路）', '瘦西湖水位站')
  AND tm >= NOW() AND tm <= DATE_ADD(NOW(), INTERVAL 24 HOUR)
  AND type = '1'
  AND r.taskid = (SELECT taskid FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1)
ORDER BY tm;
```

**注意:**
- st_mx_preset_cal_r 在 **slztk** 库，st_stbprp_b 在 **sl323** 库
- type 是 **varchar(5)**，用 `type = '1'`（不是 `type = 1`）
- 跨库查询需带库名前缀

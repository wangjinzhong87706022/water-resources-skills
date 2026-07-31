# 闸泵工况 Few-Shot 示例

> 来源: /home/scada/dataagent/domains/sqls.txt 原始 Question-SQL 对

> **⚠️ 时间锚点警示**：所有示例中的"最新"都必须锚 `MAX(tm)`，禁锚 NOW()/CURDATE()（库数据滞后于挂钟，实测停在 2026-06）。相关子查询必须带 tm 范围裁剪，禁止无界 `tm = (SELECT MAX(tm) ...)` 全分区扫描。

### Q: 查询当前开启状态的泵站最新工情、最新水情数据

```sql
SELECT p.tm AS '时间', p.stcd AS '测站编码', p.pumpname AS '泵名称',
       p.ppupz AS '站上水位（m）', p.ppdwz AS '站下水位（m）',
       p.omcn AS '开机台数', p.ompwr AS '开机功率（kw）',
       p.pmpq AS '抽水流量（m³/s）', p.ppupwptn AS '站上水势',
       p.ppdwwptn AS '站下水势', p.pdchcd AS '引排特征码', p.msqmt AS '测流方法'
FROM sl323.st_pump_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
JOIN (SELECT stcd, MAX(tm) AS mt FROM sl323.st_pump_r
      WHERE tm > DATE_SUB((SELECT MAX(tm) FROM sl323.st_pump_r), INTERVAL 30 DAY)
      GROUP BY stcd) m ON p.stcd = m.stcd AND p.tm = m.mt
WHERE b.sttp = 'DP'
  AND p.omcn > 0
ORDER BY p.tm DESC;
```

### Q: 查询所有闸站最新启闭状态

```sql
SELECT b.stnm AS '闸站名称', g.gtname AS '闸门名称', g.tm AS '更新时间',
       g.gtophgt AS '闸门开度', g.gto AS '过闸流量',
       CASE WHEN g.gtophgt > 0 THEN '已开启' ELSE '已关闭' END AS '状态'
FROM sl323.st_gate_r g
JOIN sl323.st_stbprp_b b ON g.stcd = b.stcd
JOIN (SELECT stcd, MAX(tm) AS maxTm FROM sl323.st_gate_r GROUP BY stcd) latest
  ON g.stcd = latest.stcd AND g.tm = latest.maxTm
WHERE b.sttp = 'DD'
ORDER BY g.tm DESC;
```

**注意:**
- st_gate_r **没有** upz/dwz 字段，如需上下游水位需 JOIN st_was_r
- st_gate_r PK 包含 gtname，同一测站可有多个闸门

### Q: 查询泵站综合运行状态汇总

```sql
-- 每站最新时刻仅 1 行：omcn 本身就是开机台数、pmpq 就是该站抽水流量，逐站列出即可，无需 SUM/COUNT
SELECT b.stnm AS '泵站名称',
       p.omcn AS '开机台数',
       p.pmpq AS '抽水流量',
       CASE WHEN p.pdchcd = '1' THEN '引水' WHEN p.pdchcd = '2' THEN '排水' ELSE '未知' END AS '引排特征',
       p.tm AS '时间'
FROM sl323.st_pump_r p
JOIN sl323.st_stbprp_b b ON p.stcd = b.stcd
JOIN (SELECT stcd, MAX(tm) AS mt FROM sl323.st_pump_r
      WHERE tm > DATE_SUB((SELECT MAX(tm) FROM sl323.st_pump_r), INTERVAL 30 DAY)
      GROUP BY stcd) m ON p.stcd = m.stcd AND p.tm = m.mt
WHERE b.sttp = 'DP'
ORDER BY b.stnm;
```

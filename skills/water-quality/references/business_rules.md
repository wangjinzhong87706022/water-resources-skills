# 水质业务规则

> 来源: /home/scada/dataagent/domains/evidens.txt 原文

## 水质评级标准（6级）

来源: evidens.txt "水质评级标准-*"

### CODMn (mg/L) — 高锰酸盐指数

| 等级 | 阈值 |
|------|------|
| Ⅰ类 | ≤2 |
| Ⅱ类 | (2, 4] |
| Ⅲ类 | (4, 6] |
| Ⅳ类 | (6, 10] |
| Ⅴ类 | (10, 15] |
| 劣Ⅴ类 | >15 |

### DO (mg/L) — 溶解氧

| 等级 | 阈值 |
|------|------|
| Ⅰ类 | ≥7.5 |
| Ⅱ类 | (6, 7.5] |
| Ⅲ类 | (5, 6] |
| Ⅳ类 | (3, 5] |
| Ⅴ类 | (2, 3] |
| 劣Ⅴ类 | <2 |

### NH3N (mg/L) — 氨氮

| 等级 | 阈值 |
|------|------|
| Ⅰ类 | ≤0.15 |
| Ⅱ类 | (0.15, 0.5] |
| Ⅲ类 | (0.5, 1] |
| Ⅳ类 | (1, 1.5] |
| Ⅴ类 | (1.5, 2] |
| 劣Ⅴ类 | >2 |

### TP (mg/L) — 总磷

| 等级 | 阈值 |
|------|------|
| Ⅰ类 | ≤0.02 |
| Ⅱ类 | (0.02, 0.1] |
| Ⅲ类 | (0.1, 0.2] |
| Ⅳ类 | (0.2, 0.3] |
| Ⅴ类 | (0.3, 0.4] |
| 劣Ⅴ类 | >0.4 |

## 单因子评价法

来源: evidens.txt "水质单因子评价法"

取 CODMn、NH3N、DO、TP 四项指标中**最差的等级**作为最终评价结果。
同义词: 水质综合评价, 最终水质等级, 最差等级原则

## 水质评价关联逻辑

来源: evidens.txt "水质评价关联逻辑"

查询水质数据时必须关联基础表:
```sql
FROM wq_pcp_d JOIN st_stbprp_b ON wq_pcp_d.stcd = st_stbprp_b.stcd
WHERE st_stbprp_b.sttp = 'WQ'
```

**注意:** wq_pcp_d 在 **sl325** 库，st_stbprp_b 在 **sl323** 库。跨库查询需带库名前缀。

## 预测参数类型映射

来源: evidens.txt "预测参数类型映射"

| type 值 | 参数 | 说明 |
|---------|------|------|
| 103 | DO | 溶解氧 |
| 104 | CODMn | 高锰酸盐指数（需关联 wq_cod_pz 转换） |
| 105 | TP | 总磷 |
| 128 | NH3N | 氨氮 |

**注意:** st_mx_preset_r_shj_auto.type 是 **int** 类型

## 水质预测查询规则

来源: evidens.txt "水质预测查询规则"

1. 先获取最新 taskid: `SELECT taskid FROM slztk.st_mx_taskid_shj_auto ORDER BY tm DESC LIMIT 1`
2. type=104(CODMn) 需关联 wq_cod_pz 配置表将数值转换
3. 其他参数 (DO, TP, NH3N) 直接使用 vals 原始值

同义词: 水质预测, 水质预报, 水质趋势预测, 水质预测结果

## CODMn 等级转换

来源: evidens.txt "CODMn等级转换"

当 type=104 时，需关联 wq_cod_pz 将模型输出值转换为归一化值:
```sql
SELECT value FROM wq_cod_pz WHERE min <= vals AND max > vals
```
注意: wq_cod_pz.value 是 **decimal(8,2) 归一化数值**（0~100），不是等级名称。

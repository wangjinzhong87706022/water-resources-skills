# 水位预测业务规则

> 来源: /home/scada/dataagent/domains/evidens.txt

## 河道水位预测查询规则

来源: evidens.txt "河道水位预测查询规则"

当用户查询河道、湖泊、闸站或测站的水位预测、水位预报、趋势分析、预测结果时:

1. 先获取最新 taskid:
   ```sql
   SELECT taskid FROM slztk.st_mx_taskid_r ORDER BY tm DESC LIMIT 1
   ```
2. 用 taskid 过滤预测结果表

同义词: 河道水位预测, 水位预报, 水位趋势预测, 水位预测结果

## 预测类型映射

st_mx_preset_cal_r.type 是 **varchar(5)**:

| type | 含义 |
|------|------|
| 1 | 水位 |
| 2 | 流量 |
| 3 | 闸门开启系数 |
| 24 | 入流 |
| 25 | 出流 |
| 31 | 片区降雨 |
| 33 | 净雨量 |
| 35 | 片区径流量 |

## 任务状态

st_mx_taskid_r.stuts:

| stuts | 含义 |
|-------|------|
| 0 | 计算未完成 |
| 1 | 计算完成 |

## 任务类型

st_mx_taskid_r.type:

| type | 含义 |
|------|------|
| 1 | 滚动预报 |
| 2 | 模型计算 |

## PK 注意事项

- st_mx_taskid_r 的 PK 是 **uuid**（不是 taskid）
- st_mx_preset_cal_r 无 PK，只有 INDEX

## 重点河道站点映射

（见 water-situation/references/business_rules.md）

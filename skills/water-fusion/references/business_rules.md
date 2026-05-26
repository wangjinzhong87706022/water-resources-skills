# 业务关联规则与依赖关系

> 水利系统多 Skill 跨域查询的业务规则定义

## 业务依赖规则（执行顺序）

| 规则 | 前置 Skill | 后置 Skill | 说明 |
|------|-----------|-----------|------|
| 水位预警 | water-situation | water-warning | 水位数据是预警判断的前置条件 |
| 水质预警 | water-quality | water-warning | 水质数据是水质预警的前置条件 |

## 因果关联规则（融合用）

| 规则 | Skill A | Skill B | 强度 | 方向 |
|------|---------|---------|------|------|
| 降雨→水位 | rainfall | water-situation | 1.0 | 双向 |
| 水位→预警 | water-situation | water-warning | 1.0 | 双向 |
| 水质→等级 | water-quality | water-warning | 1.0 | 双向 |
| 水位→水质 | water-situation | water-quality | 0.7 | 双向（弱） |
| 闸泵→水位 | gate-pump-operation | water-situation | 0.9 | 双向 |
| 预测→水位 | water-forecast | water-situation | 0.9 | 双向 |

## Skill-Table 映射

| Skill | 数据库 | 核心表 |
|-------|--------|--------|
| water-situation | sl323 | st_river_r, st_stbprp_b, st_rvfcch_b |
| rainfall | sl323 | st_pptn_r, st_stbprp_b |
| water-quality | sl325 | wq_pcp_d, wq_wqsinf_b, st_stbprp_b |
| water-forecast | slztk | st_mx_preset_cal_r, st_mx_taskid_r, st_stbprp_b |
| gate-pump-operation | sl323 | st_gate_r, st_was_r, st_pump_r, st_pump_pa, st_stbprp_b |
| water-warning | sl323+sl325 | st_river_r, st_rvfcch_b, st_stbprp_b, wq_pcp_d |

## 共享表（跨 Skill 关联点）

| 共享表 | 使用该表的 Skill |
|--------|-----------------|
| st_stbprp_b | 全部 6 个 skill |
| st_river_r | water-situation, water-warning |
| st_rvfcch_b | water-situation, water-warning |
| wq_pcp_d | water-quality, water-warning |

## 站名归一化规则

去掉后缀：水位站、水质站、水文站、雨量站、闸站、泵站

| 原始名称 | 归一化 |
|---------|--------|
| 古运河水位站 | 古运河 |
| 古运河水质站 | 古运河 |
| 瘦西湖水位站 | 瘦西湖 |
| 瘦西湖水质站 | 瘦西湖 |

## 冲突检测阈值

| 字段 | 阈值 | 单位 |
|------|------|------|
| 水位 | 0.05 | m |
| 流量 | 1.0 | m³/s |
| 溶解氧 | 0.5 | mg/L |
| 氨氮 | 0.1 | mg/L |
| 降雨量 | 0.5 | mm |
| 默认 | 0.01 | - |

## 消解策略

| 策略 | 适用场景 |
|------|---------|
| latest | 时序数据，取最新值 |
| average | 多源同质数据，取均值 |
| max/min | 极值场景 |
| priority | 按数据源优先级取值：water-situation > rainfall > water-quality |

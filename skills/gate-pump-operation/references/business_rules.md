# 闸泵工况业务规则

> 来源: /home/scada/dataagent/domains/evidens.txt

## 闸门 vs 堰闸区分

- **st_gate_r**（闸门启闭）: 记录闸门开度(gtophgt)、过闸流量(gto)、电气参数
- **st_was_r**（堰闸水情）: 记录上下游水位(upz/dwz)、总过闸流量(tgtq)
- **st_gate_r 没有 upz/dwz** — 如需上下游水位，必须查 st_was_r

## 闸站判断规则

- **测站类型**: sttp='DD'
- **闸门开启判断**: gtophgt > 0 表示闸门已开启
- **多闸门**: 同一测站可有多个闸门（gtname 不同），PK 包含 gtname
- **全开/全关状态**: open_state / close_state 字段

## 泵站判断规则

- **测站类型**: sttp='DP'
- **泵站运行判断**: omcn > 0 表示有泵在运行
- **引排特征码**: pdchcd='1' 引水, pdchcd='2' 排水
- **总抽水流量**: SUM(pmpq) 为所有运行泵的总流量
- **st_pump_r vs st_pump_pa**: 水情(omcn/pmpq)用 st_pump_r，工情(电气参数)用 st_pump_pa

## 泵站工情

- **st_pump_pa.switch**: 1=开, 0=关
- **st_pump_pa PK 包含 pumpname** — 每台泵一条记录
- **电气参数**: 三相电压(ua/ub/uc)、三相电流(ia/ib/ic)、有功功率(pa/pb/pc/ps)等

## 时间范围定义

来源: evidens.txt "时间范围定义"

- 某天左右: 该天前后 3 天
- 最近/最新/实时: 数据库中最大时间值对应的记录

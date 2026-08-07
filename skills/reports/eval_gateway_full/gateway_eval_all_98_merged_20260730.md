# DeerFlow Gateway 全量评测报告（98 题合并）

> 数据来源: Q001-Q063 首轮运行 + Q064-Q098 续跑（2026-07-30）


## 总体结论

- **总题数**: 98
- **平均分**: 0.847
- **通过率 (≥0.6)**: 96/98 (98.0%)
- **满分题**: 17 (17.3%)
- **平均耗时**: 251s/题, 总耗时 6.8h

## 按 Skill 统计

| Skill | 题数 | 平均分 | 通过率 | 满分 | 平均耗时 | 平均轮次 |
|---|---|---|---|---|---|---|
| rainfall | 18 | 0.890 | 100% | 6 | 202s | 10.1 |
| gate-pump-operation | 15 | 0.880 | 100% | 3 | 263s | 7.1 |
| water-situation | 25 | 0.867 | 96% | 7 | 321s | 6.7 |
| water-quality | 13 | 0.812 | 100% | 0 | 248s | 10.8 |
| water-warning | 14 | 0.798 | 100% | 0 | 176s | 7.6 |
| water-forecast | 13 | 0.795 | 92% | 1 | 255s | 10.9 |

## 按难度统计

| Level | 题数 | 平均分 | 通过率 | 平均耗时 |
|---|---|---|---|---|
| L1 | 15 | 0.870 | 100% | 271s |
| L2 | 21 | 0.861 | 100% | 261s |
| L3 | 62 | 0.836 | 97% | 243s |

## 低分题（< 0.6）

| Q# | Skill | Level | Score | 耗时 | 问题 |
|---|---|---|---|---|---|
| Q063 | water-forecast | L3 | 0.390 | 20s | 查询河道断面数据（某任务下的所有断面水位）。 |
| Q020 | water-situation | L3 | 0.490 | 374s | 扬州水利枢纽3月份平均水位。 |

## 最慢 5 题

| Q# | Skill | Level | 耗时 | 轮次 | Score |
|---|---|---|---|---|---|
| Q009 | water-situation | L2 | 882s | 6 | 0.977 |
| Q014 | water-situation | L3 | 864s | 24 | 0.894 |
| Q004 | water-situation | L1 | 768s | 8 | 0.790 |
| Q059 | water-forecast | L2 | 750s | 25 | 0.740 |
| Q062 | water-forecast | L3 | 569s | 20 | 0.740 |

## 全部明细

| Q# | Skill | Level | Score | SQLs | Rounds | 耗时 | 状态 |
|---|---|---|---|---|---|---|---|
| Q001 | water-situation | L1 | 0.790 | 1 | 3 | 396s | ✓ |
| Q002 | water-situation | L1 | 1.000 | 1 | 4 | 421s | ✓ |
| Q003 | water-situation | L1 | 1.000 | 1 | 3 | 15s | ✓ |
| Q004 | water-situation | L1 | 0.790 | 6 | 8 | 768s | ✓ |
| Q005 | water-situation | L2 | 0.790 | 4 | 6 | 38s | ✓ |
| Q006 | water-situation | L2 | 1.000 | 2 | 3 | 22s | ✓ |
| Q007 | water-situation | L2 | 0.900 | 2 | 4 | 38s | ✓ |
| Q008 | water-situation | L2 | 1.000 | 2 | 5 | 358s | ✓ |
| Q009 | water-situation | L2 | 0.977 | 3 | 6 | 882s | ✓ |
| Q010 | water-situation | L2 | 0.806 | 1 | 4 | 487s | ✓ |
| Q011 | water-situation | L3 | 0.850 | 4 | 7 | 302s | ✓ |
| Q012 | water-situation | L3 | 0.863 | 3 | 12 | 467s | ✓ |
| Q013 | water-situation | L3 | 0.850 | 5 | 8 | 270s | ✓ |
| Q014 | water-situation | L3 | 0.894 | 13 | 24 | 864s | ✓ |
| Q015 | water-situation | L3 | 1.000 | 4 | 7 | 455s | ✓ |
| Q016 | water-situation | L3 | 1.000 | 1 | 3 | 27s | ✓ |
| Q017 | water-situation | L3 | 1.000 | 1 | 3 | 24s | ✓ |
| Q018 | water-situation | L3 | 0.850 | 1 | 4 | 134s | ✓ |
| Q019 | water-situation | L3 | 0.790 | 2 | 5 | 417s | ✓ |
| Q020 | water-situation | L3 | 0.490 | 12 | 13 | 374s | ✓ |
| Q021 | water-situation | L3 | 0.850 | 1 | 4 | 124s | ✓ |
| Q022 | water-situation | L3 | 0.790 | 6 | 7 | 289s | ✓ |
| Q023 | water-situation | L3 | 0.740 | 7 | 12 | 319s | ✓ |
| Q024 | water-situation | L3 | 0.800 | 10 | 8 | 338s | ✓ |
| Q025 | water-situation | L3 | 0.850 | 1 | 4 | 196s | ✓ |
| Q026 | rainfall | L1 | 0.790 | 4 | 7 | 283s | ✓ |
| Q027 | rainfall | L1 | 1.000 | 5 | 7 | 235s | ✓ |
| Q028 | rainfall | L1 | 0.800 | 10 | 13 | 257s | ✓ |
| Q029 | rainfall | L2 | 0.900 | 3 | 5 | 103s | ✓ |
| Q030 | rainfall | L2 | 0.850 | 4 | 7 | 163s | ✓ |
| Q031 | rainfall | L2 | 0.790 | 5 | 8 | 117s | ✓ |
| Q032 | rainfall | L3 | 0.800 | 6 | 10 | 179s | ✓ |
| Q033 | rainfall | L3 | 0.950 | 6 | 14 | 389s | ✓ |
| Q034 | rainfall | L3 | 1.000 | 4 | 7 | 111s | ✓ |
| Q035 | rainfall | L3 | 0.800 | 8 | 9 | 256s | ✓ |
| Q036 | rainfall | L3 | 1.000 | 1 | 4 | 115s | ✓ |
| Q037 | rainfall | L3 | 1.000 | 4 | 6 | 120s | ✓ |
| Q038 | rainfall | L3 | 1.000 | 3 | 6 | 134s | ✓ |
| Q039 | rainfall | L3 | 1.000 | 2 | 5 | 30s | ✓ |
| Q040 | rainfall | L3 | 0.866 | 30 | 27 | 475s | ✓ |
| Q041 | rainfall | L3 | 0.790 | 6 | 6 | 37s | ✓ |
| Q042 | rainfall | L3 | 0.740 | 15 | 25 | 351s | ✓ |
| Q043 | rainfall | L3 | 0.950 | 13 | 15 | 284s | ✓ |
| Q044 | water-quality | L1 | 0.850 | 2 | 5 | 34s | ✓ |
| Q045 | water-quality | L1 | 0.850 | 4 | 7 | 118s | ✓ |
| Q046 | water-quality | L2 | 0.740 | 8 | 18 | 533s | ✓ |
| Q047 | water-quality | L2 | 0.850 | 4 | 8 | 42s | ✓ |
| Q048 | water-quality | L2 | 0.800 | 8 | 11 | 402s | ✓ |
| Q049 | water-quality | L3 | 0.740 | 7 | 14 | 318s | ✓ |
| Q050 | water-quality | L3 | 0.950 | 11 | 23 | 372s | ✓ |
| Q051 | water-quality | L3 | 0.790 | 2 | 4 | 28s | ✓ |
| Q052 | water-quality | L3 | 0.850 | 3 | 8 | 376s | ✓ |
| Q053 | water-quality | L3 | 0.740 | 7 | 15 | 229s | ✓ |
| Q054 | water-quality | L3 | 0.850 | 2 | 5 | 36s | ✓ |
| Q055 | water-quality | L3 | 0.740 | 5 | 12 | 376s | ✓ |
| Q056 | water-quality | L3 | 0.800 | 5 | 11 | 363s | ✓ |
| Q057 | water-forecast | L1 | 0.740 | 8 | 21 | 352s | ✓ |
| Q058 | water-forecast | L1 | 0.987 | 3 | 7 | 27s | ✓ |
| Q059 | water-forecast | L2 | 0.740 | 10 | 25 | 750s | ✓ |
| Q060 | water-forecast | L2 | 0.790 | 4 | 8 | 231s | ✓ |
| Q061 | water-forecast | L2 | 1.000 | 2 | 4 | 71s | ✓ |
| Q062 | water-forecast | L3 | 0.740 | 22 | 20 | 569s | ✓ |
| Q063 | water-forecast | L3 | 0.390 | 0 | 3 | 20s | ✓ |
| Q064 | water-forecast | L3 | 0.880 | 3 | 8 | 170s | ✓ |
| Q065 | water-forecast | L3 | 0.740 | 8 | 13 | 438s | ✓ |
| Q066 | water-forecast | L3 | 0.900 | 5 | 8 | 200s | ✓ |
| Q067 | water-forecast | L3 | 0.740 | 4 | 11 | 240s | ✓ |
| Q068 | water-forecast | L3 | 0.900 | 5 | 7 | 212s | ✓ |
| Q069 | water-forecast | L3 | 0.790 | 4 | 7 | 42s | ✓ |
| Q070 | gate-pump-operation | L1 | 0.881 | 1 | 5 | 452s | ✓ |
| Q071 | gate-pump-operation | L1 | 0.850 | 1 | 4 | 39s | ✓ |
| Q072 | gate-pump-operation | L2 | 0.900 | 6 | 9 | 382s | ✓ |
| Q073 | gate-pump-operation | L2 | 0.850 | 8 | 7 | 267s | ✓ |
| Q074 | gate-pump-operation | L2 | 1.000 | 4 | 8 | 214s | ✓ |
| Q075 | gate-pump-operation | L3 | 0.850 | 6 | 8 | 214s | ✓ |
| Q076 | gate-pump-operation | L3 | 0.700 | 4 | 7 | 217s | ✓ |
| Q077 | gate-pump-operation | L3 | 0.800 | 8 | 10 | 334s | ✓ |
| Q078 | gate-pump-operation | L3 | 0.850 | 5 | 8 | 261s | ✓ |
| Q079 | gate-pump-operation | L3 | 1.000 | 2 | 5 | 217s | ✓ |
| Q080 | gate-pump-operation | L3 | 0.950 | 5 | 9 | 231s | ✓ |
| Q081 | gate-pump-operation | L3 | 0.790 | 3 | 6 | 50s | ✓ |
| Q082 | gate-pump-operation | L3 | 1.000 | 4 | 7 | 430s | ✓ |
| Q083 | gate-pump-operation | L3 | 0.984 | 2 | 3 | 154s | ✓ |
| Q084 | gate-pump-operation | L3 | 0.800 | 11 | 10 | 481s | ✓ |
| Q085 | water-warning | L1 | 0.821 | 9 | 10 | 364s | ✓ |
| Q086 | water-warning | L1 | 0.900 | 4 | 7 | 309s | ✓ |
| Q087 | water-warning | L2 | 0.850 | 2 | 5 | 127s | ✓ |
| Q088 | water-warning | L2 | 0.800 | 8 | 11 | 150s | ✓ |
| Q089 | water-warning | L2 | 0.750 | 5 | 9 | 105s | ✓ |
| Q090 | water-warning | L3 | 0.720 | 7 | 7 | 148s | ✓ |
| Q091 | water-warning | L3 | 0.777 | 4 | 7 | 109s | ✓ |
| Q092 | water-warning | L3 | 0.850 | 9 | 6 | 164s | ✓ |
| Q093 | water-warning | L3 | 0.794 | 1 | 6 | 129s | ✓ |
| Q094 | water-warning | L3 | 0.740 | 6 | 9 | 128s | ✓ |
| Q095 | water-warning | L3 | 0.850 | 5 | 6 | 116s | ✓ |
| Q096 | water-warning | L3 | 0.800 | 3 | 9 | 361s | ✓ |
| Q097 | water-warning | L3 | 0.732 | 5 | 8 | 145s | ✓ |
| Q098 | water-warning | L3 | 0.790 | 8 | 7 | 114s | ✓ |

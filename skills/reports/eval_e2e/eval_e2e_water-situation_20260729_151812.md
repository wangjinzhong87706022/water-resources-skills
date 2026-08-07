# DeerFlow 端到端评测报告

> 模式: **直连 OpenAI API**（模拟 DeerFlow first-pass）
> 模型: Qwen3.6-27B-Q5_K_S.gguf
> 端点: http://172.28.101.81:8080/v1

- 时间: 20260729_151812
- Skill: water-situation
- Timeout: 120s
- 用例数: 2 | 完成: 2 | 超时: 0 | 平均分: 0.745

## 结果明细

| Q# | Skill | Level | Score | Code Type | Status | Duration |
|---|---|---|---|---|---|---|
| Q001 | water-situation | L1 | 0.790 | python | ✓ | 11.1s |
| Q002 | water-situation | L1 | 0.700 | python | ✓ | 4.1s |

## 低分 Case（< 0.5）

### Q002 [water-situation/L1] - 0.700

**Q**: 查询宝应水位站的所属河流、水系、流域、测站类别。

**Response** (前500字):
```
我来查询宝应水位站的详细信息。

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

sql = """
SELECT 
    stcd AS 站码,
    stnm AS 测站名称,
    sttp AS 测站类别,
    rvnm AS 所属河流,
    hnnm AS 水系,
    bsnm AS 流域,
    addvcd AS 行政区划码,
    dtmnm AS 高程基准,
    esstym AS 建站年月
FROM sl323.st_stbprp_b
WHERE stnm LIKE '%宝应%'
LIMIT 10
"""

result = query(sql)
print(result)
```
```

**Extracted Code**:
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

sql = """
SELECT 
    stcd AS 站码,
    stnm AS 测站名称,
    sttp AS 测站类别,
    rvnm AS 所属河流,
    hnnm AS 水系,
    bsnm AS 流域,
    addvcd AS 行政区划码,
    dtmnm AS 高程基准,
    esstym AS 建站年月
FROM sl323.st_stbprp_b
WHERE stnm LIKE '%宝应%'
LIMIT 10
"""

result = query(sql)
print(result)
```

---

### Q001 [water-situation/L1] - 0.790

**Q**: 古运河有哪些水位测站？

**Response** (前500字):
```
我来查询古运河的水位测站信息。

```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

sql = """
SELECT 
    b.stcd AS 站码,
    b.stnm AS 站名,
    b.sttp AS 站类,
    b.rvnm AS 河流名称,
    b.hnnm AS 水系名称,
    b.bsnm AS 流域名称,
    b.addvcd AS 行政区划码,
    b.dtmnm AS 高程基准,
    b.esstym AS 建站年月
FROM st_stbprp_b b
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
    AND b.sttp IN ('ZZ', 'ZQ')
ORDER BY b.stcd
"""

result = query(sql)
print(f"共找到 {len(resu
```

**Extracted Code**:
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

sql = """
SELECT 
    b.stcd AS 站码,
    b.stnm AS 站名,
    b.sttp AS 站类,
    b.rvnm AS 河流名称,
    b.hnnm AS 水系名称,
    b.bsnm AS 流域名称,
    b.addvcd AS 行政区划码,
    b.dtmnm AS 高程基准,
    b.esstym AS 建站年月
FROM st_stbprp_b b
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
    AND b.sttp IN ('ZZ', 'ZQ')
ORDER BY b.stcd
"""

result = query(sql)
print(f"共找到 {len(result)} 个古运河水位测站：")
print("-" 
```

---


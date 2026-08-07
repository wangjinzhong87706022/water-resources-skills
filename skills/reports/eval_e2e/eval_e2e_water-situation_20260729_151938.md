# DeerFlow 端到端评测报告

> 模式: **直连 OpenAI API**（模拟 DeerFlow first-pass）
> 模型: Qwen3.6-27B-Q5_K_S.gguf
> 端点: http://172.28.101.81:8080/v1

- 时间: 20260729_151938
- Skill: water-situation
- Timeout: 120s
- 用例数: 2 | 完成: 2 | 超时: 0 | 平均分: 0.550

## 结果明细

| Q# | Skill | Level | Score | Code Type | Status | Duration |
|---|---|---|---|---|---|---|
| Q001 | water-situation | L1 | 0.400 | python | ✗ | 9.6s |
| Q002 | water-situation | L1 | 0.700 | python | ✓ | 6.2s |

## 低分 Case（< 0.5）

### Q001 [water-situation/L1] - 0.400

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
    b.stcd,
    b.stnm AS station_name,
    b.sttp AS station_type,
    b.rvnm AS river_name,
    b.hnnm AS water_system,
    b.bsnm AS basin,
    b.addvcd AS admin_code,
    b.esstym AS establishment_date,
    b.dtmnm AS elevation_datum
FROM st_stbp_b b
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
ORDER BY b.stcd
"""

results = query
```

**Extracted Code**:
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

sql = """
SELECT 
    b.stcd,
    b.stnm AS station_name,
    b.sttp AS station_type,
    b.rvnm AS river_name,
    b.hnnm AS water_system,
    b.bsnm AS basin,
    b.addvcd AS admin_code,
    b.esstym AS establishment_date,
    b.dtmnm AS elevation_datum
FROM st_stbp_b b
WHERE (b.stnm LIKE '%古运河%' OR b.rvnm LIKE '%古运河%')
ORDER BY b.stcd
"""

results = query(sql)
print(f"共找到 {len(resu
```

**Error**: Traceback (most recent call last):
  File "/tmp/tmpv5enct5c.py", line 21, in <module>
    results = query(sql)
              ^^^^^^^^^^
  File "/opt/git/water-resources-skills/skills/lib/db.py", line 117, in query
    cur.execute(sql)
  File "/opt/git/hermes-agent/venv/lib/python3.11/site-packages/pymysql/cursors.py", line 153, in execute
    result = self._query(query)
             ^^^^^^^^^^^^^^^^^^
  File "/opt/git/hermes-agent/venv/lib/python3.11/site-packages/pymysql/cursors.py", line 322, in _query
    conn.query(q)
  File "/opt/git/hermes-agent/venv/lib/python3.11/site-packages/pymysql/connections.py", line 575, in query
    self._affected_rows = self._read_query_result(unbuffered=unbuffered)
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/git/hermes-agent/venv/lib/python3.11/site-packages/pymysql/connections.py", line 826, in _read_query_result
    result.read()
  File "/opt/git/hermes-agent/venv/lib/python3.11/site-packages/pymysql/connections.py", line 1203, in read
    first_packet = self.connection._read_packet()
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/git/hermes-agent/venv/lib/python3.11/site-packages/pymysql/connections.py", line 782, in _read_packet
    packet.raise_for_error()
  File "/opt/git/hermes-agent/venv/lib/python3.11/site-packages/pymysql/protocol.py", line 219, in raise_for_error
    err.raise_mysql_exception(self._data)
  File "/opt/git/hermes-agent/venv/lib/python3.11/site-packages/pymysql/err.py", line 150, in raise_mysql_exception
    raise errorclass(errno, errval)
pymysql.err.ProgrammingError: (1146, "Table 'sl323.st_stbp_b' doesn't exist")

---

### Q002 [water-situation/L1] - 0.700

**Q**: 查询宝应水位站的所属河流、水系、流域、测站类别。

**Response** (前500字):
```
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

sql = """
SELECT 
    b.stcd AS 站点编码,
    b.stnm AS 站点名称,
    b.rvnm AS 所属河流,
    b.hnnm AS 所属水系,
    b.bsnm AS 所属流域,
    b.sttp AS 测站类型代码,
    CASE b.sttp 
        WHEN 'ZZ' THEN '水位站'
        WHEN 'ZQ' THEN '水文站'
        WHEN 'RR' THEN '水库站'
        WHEN 'YC' THEN '雨量站'
        WHEN 'PQ' THEN '泵站站'
        WHEN 'GZ' THEN '闸门站'
        ELSE b.sttp 
    END AS 测站类别,
    b.dt
```

**Extracted Code**:
```python
import os, sys
sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
from db import query

sql = """
SELECT 
    b.stcd AS 站点编码,
    b.stnm AS 站点名称,
    b.rvnm AS 所属河流,
    b.hnnm AS 所属水系,
    b.bsnm AS 所属流域,
    b.sttp AS 测站类型代码,
    CASE b.sttp 
        WHEN 'ZZ' THEN '水位站'
        WHEN 'ZQ' THEN '水文站'
        WHEN 'RR' THEN '水库站'
        WHEN 'YC' THEN '雨量站'
        WHEN 'PQ' THEN '泵站站'
        WHEN 'GZ' THEN '闸门站'
        ELSE b.sttp 
    END AS 测站类别,
    b.dtmnm AS 高程基
```

---


#!/usr/bin/env python3
"""
补充查询：洪泽湖警戒水位、GRZ值、sttp含义
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from db import query

def print_section(title):
    print(f"\n{'='*60}")
    print(f"【{title}】")
    print(f"{'='*60}")

def print_query(sql):
    print(f"\n执行查询:\n{sql}\n")

# ========== 补充1: 洪泽湖蒋坝站的阈值 ==========
print_section("补充1: 洪泽湖蒋坝站(50916500)的阈值查询")

sql = """
SELECT stcd, WRZ, GRZ, WRQ, GRQ, FLPQ, LDKEL, RDKEL
FROM sl323.st_rvfcch_b
WHERE stcd = '50916500'
"""
result = query(sql)
print(f"✓ 洪泽湖蒋坝站阈值:")
if result:
    for row in result:
        print(f"  {row}")
else:
    print("  (无数据)")

# 尝试用蒋坝的 stcd 前缀模糊查询
sql2 = """
SELECT stcd, WRZ, GRZ
FROM sl323.st_rvfcch_b
WHERE stcd LIKE '509165%'
"""
result2 = query(sql2)
print(f"\n模糊匹配 stcd='509165%':")
for row in result2:
    print(f"  {row}")

# ========== 补充2: GRZ 非空记录 ==========
print_section("补充2: GRZ 非空记录 (保证水位)")

sql_grz = """
SELECT stcd, WRZ, GRZ
FROM sl323.st_rvfcch_b
WHERE GRZ IS NOT NULL
ORDER BY GRZ DESC
LIMIT 20
"""
result_grz = query(sql_grz)
print(f"✓ 找到 {len(result_grz)} 条 GRZ 非空记录 (前20条):")
for row in result_grz:
    print(f"  {row}")

# ========== 补充3: sttp 含义 ==========
print_section("补充3: sttp 测站类型代码统计")

sql_sttp = """
SELECT sttp, COUNT(DISTINCT stcd) as cnt
FROM sl323.st_stbprp_b
WHERE rvnm IN ('洪泽湖', '里运河', '长江')
   OR stnm LIKE '%洪泽湖%'
   OR stnm LIKE '%里运河%'
   OR stnm LIKE '%长江%'
GROUP BY sttp
ORDER BY cnt DESC
"""
result_sttp = query(sql_sttp)
print(f"✓ 测站类型分布:")
for row in result_sttp:
    print(f"  {row}")

# 查询全部 sttp 类型分布
sql_all_sttp = """
SELECT sttp, COUNT(DISTINCT stcd) as total_cnt
FROM sl323.st_stbprp_b
GROUP BY sttp
ORDER BY total_cnt DESC
LIMIT 20
"""
result_all_sttp = query(sql_all_sttp)
print(f"\n全部测站类型分布 (前20):")
for row in result_all_sttp:
    print(f"  {row}")

# ========== 补充4: 洪泽湖相关所有测站 ==========
print_section("补充4: 洪泽湖所有测站详细信息")

sql_hongze_all = """
SELECT stcd, stnm, rvnm, sttp, dtmel, dtmnm
FROM sl323.st_stbprp_b
WHERE rvnm = '洪泽湖'
   OR stnm LIKE '%洪泽湖%'
   OR stnm LIKE '%蒋坝%'
   OR stnm LIKE '%洪泽%'
"""
result_hongze_all = query(sql_hongze_all)
print(f"✓ 洪泽湖相关测站:")
for row in result_hongze_all:
    print(f"  {row}")

# ========== 补充5: LDKEL / RDKEL 字段 ==========
print_section("补充5: LDKEL / RDKEL 字段含义验证")

sql_ldkel = """
SELECT stcd, LDKEL, RDKEL, WRZ, GRZ
FROM sl323.st_rvfcch_b
WHERE LDKEL IS NOT NULL OR RDKEL IS NOT NULL
LIMIT 20
"""
result_ldkel = query(sql_ldkel)
print(f"✓ 有 LDKEL/RDKEL 值的记录:")
for row in result_ldkel:
    print(f"  {row}")

print_section("补充验证完成")

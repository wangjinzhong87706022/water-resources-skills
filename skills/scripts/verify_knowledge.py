#!/usr/bin/env python3
"""
水利知识点验证脚本 - 最终版
验证案例中的四个关键知识点
"""
import os
import sys
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ 已加载 .env 文件: {env_path}")
else:
    print(f"✗ 警告: .env 文件不存在")

# 添加 lib 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

from db import query

def print_section(title):
    print(f"\n{'='*60}")
    print(f"【{title}】")
    print(f"{'='*60}")

def print_query(sql):
    print(f"\n执行查询:\n{sql}\n")

# ========== 1. 水体分类验证 ==========
print_section("1. 水体分类验证")

sql = """
SELECT stcd, stnm, rvnm, sttp
FROM sl323.st_stbprp_b
WHERE rvnm IN ('洪泽湖', '里运河', '长江')
   OR stnm LIKE '%洪泽湖%'
   OR stnm LIKE '%里运河%'
   OR stnm LIKE '%长江%'
LIMIT 50
"""
result = query(sql)
print(f"✓ 找到 {len(result)} 条记录:")
for row in result:
    print(f"  {row}")

# ========== 2. 测站数量验证 ==========
print_section("2. 测站数量验证（样本权重）")

sql = """
SELECT rvnm, COUNT(DISTINCT stcd) as station_count
FROM sl323.st_stbprp_b
WHERE rvnm IN ('洪泽湖', '里运河', '长江')
   OR stnm LIKE '%洪泽湖%'
   OR stnm LIKE '%里运河%'
   OR stnm LIKE '%长江%'
GROUP BY rvnm
"""
result = query(sql)
print(f"✓ 测站数量统计:")
for row in result:
    print(f"  {row}")

# ========== 3. 高程基准信息验证 ==========
print_section("3. 高程基准信息验证")

sql = "DESCRIBE sl323.st_stbprp_b"
result = query(sql)
print(f"✓ st_stbprp_b 表结构 (共 {len(result)} 个字段):")
for row in result:
    if row['Field'] in ['stcd', 'stnm', 'rvnm', 'dtmel', 'dtmnm', 'dtpr']:
        print(f"  ★ {row['Field']:15s} {row['Type']:20s}")

print("\n查询有高程值的测站 (针对洪泽湖、里运河、长江):")
sql_dtmel = """
SELECT stcd, stnm, rvnm, dtmel, dtmnm
FROM sl323.st_stbprp_b
WHERE dtmel IS NOT NULL
  AND (rvnm IN ('洪泽湖', '里运河', '长江')
       OR stnm LIKE '%洪泽湖%'
       OR stnm LIKE '%里运河%'
       OR stnm LIKE '%长江%')
LIMIT 20
"""
result_dtmel = query(sql_dtmel)
print(f"✓ 找到 {len(result_dtmel)} 条高程记录:")
for row in result_dtmel:
    print(f"  {row}")

# ========== 4. 警戒水位/阈值验证 ==========
print_section("4. 警戒水位/阈值验证")

sql_struct = "DESCRIBE sl323.st_rvfcch_b"
result_struct = query(sql_struct)
print(f"✓ st_rvfcch_b 表结构 (共 {len(result_struct)} 个字段):")
for row in result_struct:
    print(f"  {row['Field']:25s} {row['Type']:20s}")

# 查看 sample 数据
sql_sample = "SELECT * FROM sl323.st_rvfcch_b LIMIT 3"
result_sample = query(sql_sample)
print(f"\n✓ 样本数据 (前3条):")
if result_sample:
    for row in result_sample:
        # 只打印有值的字段
        filtered = {k: v for k, v in row.items() if v is not None}
        print(f"  {filtered}")

# 查询 WRZ 和 GRZ
print("\n查询警戒水位(WRZ)和保证水位(GRZ):")
sql_wrz = """
SELECT stcd, WRZ, GRZ
FROM sl323.st_rvfcch_b
WHERE WRZ IS NOT NULL OR GRZ IS NOT NULL
ORDER BY WRZ DESC
LIMIT 50
"""
result_wrz = query(sql_wrz)
print(f"✓ 找到 {len(result_wrz)} 条水位阈值记录 (前50条):")
for row in result_wrz:
    print(f"  {row}")

# 特别关注洪泽湖警戒水位 14.35m
print("\n洪泽湖警戒水位 14.35m 验证:")
sql_hongze = """
SELECT stcd, WRZ, GRZ
FROM sl323.st_rvfcch_b
WHERE WRZ BETWEEN 14.0 AND 14.5
   OR GRZ BETWEEN 14.0 AND 14.5
LIMIT 20
"""
result_hongze = query(sql_hongze)
print(f"✓ 找到 {len(result_hongze)} 条接近 14.35m 的记录:")
for row in result_hongze:
    print(f"  {row}")

# 通过 MAIN_RV 字段尝试匹配
print("\n通过 MAIN_RV 字段匹配河流名称:")
sql_main_rv = """
SELECT DISTINCT MAIN_RV
FROM sl323.st_rvfcch_b
WHERE MAIN_RV IS NOT NULL
ORDER BY MAIN_RV
LIMIT 50
"""
result_main_rv = query(sql_main_rv)
print(f"✓ MAIN_RV 字段值:")
for row in result_main_rv:
    print(f"  {row}")

# 尝试获取特定河流的阈值
if result_main_rv:
    main_rv_list = [row['MAIN_RV'] for row in result_main_rv if any(kw in row.get('MAIN_RV', '') for kw in ['洪泽', '长江', '运河'])]
    if main_rv_list:
        print(f"\n找到相关河流: {main_rv_list}")
        for rv in main_rv_list[:5]:
            sql_rv = f"""
            SELECT stcd, WRZ, GRZ
            FROM sl323.st_rvfcch_b
            WHERE MAIN_RV = '{rv}'
            LIMIT 10
            """
            result_rv = query(sql_rv)
            print(f"\n{rv} 的阈值数据:")
            for row in result_rv:
                print(f"  {row}")

print_section("验证完成")

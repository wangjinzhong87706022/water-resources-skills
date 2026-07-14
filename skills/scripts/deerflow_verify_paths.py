#!/usr/bin/env python3
"""
DeerFlow Skill 路径注入验证脚本

验证在注入 WATER_RESOURCES_ROOT 环境变量后：
1. lib/db.py 能否正确加载
2. 共享文档能否正确读取
3. 标准导入片段是否工作
"""
import os
import sys
from pathlib import Path

print("=" * 70)
print("DeerFlow Skill 路径注入验证")
print("=" * 70)

# 检查环境变量
print("\n[1] 环境变量检查")
print("-" * 70)

water_root = os.environ.get('WATER_RESOURCES_ROOT')
if water_root:
    print(f"✅ WATER_RESOURCES_ROOT={water_root}")
    root_path = Path(water_root)
    if not root_path.exists():
        print(f"❌ 路径不存在: {water_root}")
        sys.exit(1)
else:
    print("❌ WATER_RESOURCES_ROOT 未设置")
    print("   请先运行: export WATER_RESOURCES_ROOT=/mnt/skills")
    sys.exit(1)

# 验证 lib/ 目录
print("\n[2] lib/ 目录验证")
print("-" * 70)
lib_path = root_path / 'lib'
print(f"lib_path = {lib_path}")

if not lib_path.exists():
    print(f"❌ lib/ 目录不存在: {lib_path}")
    sys.exit(1)

if not (lib_path / 'db.py').exists():
    print(f"❌ db.py 不存在: {lib_path / 'db.py'}")
    sys.exit(1)

print(f"✅ lib/db.py 存在")

# 验证 shared/ 目录
print("\n[3] shared/ 目录验证")
print("-" * 70)
shared_path = root_path / 'shared'
print(f"shared_path = {shared_path}")

if not shared_path.exists():
    print(f"❌ shared/ 目录不存在: {shared_path}")
    sys.exit(1)

if not (shared_path / 'db_connection.md').exists():
    print(f"❌ db_connection.md 不存在: {shared_path / 'db_connection.md'}")
    sys.exit(1)

print(f"✅ shared/db_connection.md 存在")

# 验证 water-situation skill
print("\n[4] water-situation skill 验证")
print("-" * 70)
skill_path = root_path / 'water-situation'
print(f"skill_path = {skill_path}")

if not skill_path.exists():
    print(f"❌ water-situation/ 目录不存在: {skill_path}")
    sys.exit(1)

if not (skill_path / 'SKILL.md').exists():
    print(f"❌ SKILL.md 不存在: {skill_path / 'SKILL.md'}")
    sys.exit(1)

print(f"✅ water-situation/SKILL.md 存在")

# 测试标准导入片段
print("\n[5] 测试标准导入片段（LLM 运行时路径）")
print("-" * 70)

try:
    sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))
    from db import query, query_multi
    print(f"✅ 成功导入 db.query 和 db.query_multi")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)
except KeyError as e:
    print(f"❌ 环境变量缺失: {e}")
    sys.exit(1)

# 测试实际查询
print("\n[6] 测试实际数据库查询")
print("-" * 70)

try:
    # 查询测站总数
    rows = query("SELECT COUNT(*) AS cnt FROM sl323.st_stbprp_b")
    if rows:
        cnt = rows[0]['cnt']
        print(f"✅ 查询成功: sl323.st_stbprp_b 共有 {cnt} 个测站")
    else:
        print(f"⚠️  查询返回空结果")
except Exception as e:
    print(f"❌ 查询失败: {e}")
    print(f"   请确认 SL323_DB_PASSWORD 已设置且数据库可连接")
    sys.exit(1)

# 测试 bootstrap 解析器
print("\n[7] 测试 bootstrap 解析器（离线脚本路径）")
print("-" * 70)

try:
    # 从 scripts 目录运行时的路径
    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir.parent / 'lib'))
    from bootstrap import locate_lib, locate_shared

    lib_resolved = locate_lib()
    shared_resolved = locate_shared()
    print(f"✅ bootstrap.locate_lib()  = {lib_resolved}")
    print(f"✅ bootstrap.locate_shared() = {shared_resolved}")

    # 验证与 WATER_RESOURCES_ROOT 一致
    if lib_resolved == root_path / 'lib':
        print(f"✅ lib 路径与 WATER_RESOURCES_ROOT 一致")
    else:
        print(f"⚠️  lib 路径不一致: {lib_resolved} vs {root_path / 'lib'}")

except Exception as e:
    print(f"❌ bootstrap 解析失败: {e}")
    sys.exit(1)

# 验证 references
print("\n[8] 验证 skill references/ 目录")
print("-" * 70)
ref_path = skill_path / 'references'
if ref_path.exists():
    refs = list(ref_path.glob('*.md'))
    print(f"✅ references/ 存在，包含 {len(refs)} 个文件")
    for ref in sorted(refs)[:5]:  # 显示前5个
        print(f"   - {ref.name}")
    if len(refs) > 5:
        print(f"   ... 还有 {len(refs) - 5} 个")
else:
    print(f"⚠️  references/ 目录不存在")

print("\n" + "=" * 70)
print("✅ 所有验证通过！")
print("=" * 70)
print(f"\nDeerFlow 配置:")
print(f"  WATER_RESOURCES_ROOT={water_root}")
print(f"  → lib/ 解析: $WATER_RESOURCES_ROOT/lib")
print(f"  → shared/ 解析: $WATER_RESOURCES_ROOT/shared")
print(f"\nLLM 运行时标准导入片段:")
print(f"  import os, sys")
print(f"  sys.path.insert(0, os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib'))")
print(f"  from db import query, query_multi")
print()

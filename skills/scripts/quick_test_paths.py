#!/usr/bin/env python3
"""
快速测试: 验证 WATER_RESOURCES_ROOT 路径注入是否工作
不依赖数据库连接，仅测试路径解析
"""
import os
import sys
from pathlib import Path

print("=" * 70)
print("快速路径注入测试（无需数据库）")
print("=" * 70)

# 测试 1: 环境变量
print("\n[1] 环境变量检查")
water_root = os.environ.get('WATER_RESOURCES_ROOT')
if water_root:
    print(f"✅ WATER_RESOURCES_ROOT={water_root}")
else:
    print(f"❌ WATER_RESOURCES_ROOT 未设置")
    print(f"   请先运行: export WATER_RESOURCES_ROOT=/mnt/skills")
    sys.exit(1)

# 测试 2: lib 路径
print("\n[2] lib/ 路径解析")
lib_path = Path(water_root) / 'lib'
db_file = lib_path / 'db.py'
print(f"lib_path = {lib_path}")

if not lib_path.exists():
    print(f"⚠️  /mnt/skills/lib 在本地不存在（正常，它是 DeerFlow 虚拟路径）")
    print(f"   在 DeerFlow sandbox 中此路径应该存在")
else:
    if db_file.exists():
        print(f"✅ lib/db.py 存在")
    else:
        print(f"❌ lib/db.py 不存在")

# 测试 3: shared 路径
print("\n[3] shared/ 路径解析")
shared_path = Path(water_root) / 'shared'
conn_file = shared_path / 'db_connection.md'
print(f"shared_path = {shared_path}")

if not shared_path.exists():
    print(f"⚠️  /mnt/skills/shared 在本地不存在（正常，它是 DeerFlow 虚拟路径）")
else:
    if conn_file.exists():
        print(f"✅ shared/db_connection.md 存在")
    else:
        print(f"❌ shared/db_connection.md 不存在")

# 测试 4: 标准导入片段解析
print("\n[4] 标准导入片段解析")
try:
    lib_str = os.path.join(os.environ['WATER_RESOURCES_ROOT'], 'lib')
    print(f"解析结果: sys.path.insert(0, {lib_str})")
    print(f"✅ 片段格式正确")
except KeyError:
    print(f"❌ WATER_RESOURCES_ROOT 不在环境变量中")
    sys.exit(1)

# 测试 5: skill 路径
print("\n[5] water-situation skill 路径")
skill_path = Path(water_root) / 'water-situation' / 'SKILL.md'
print(f"skill_path = {skill_path}")

if not skill_path.exists():
    print(f"⚠️  /mnt/skills/water-situation/SKILL.md 在本地不存在")
    print(f"   （这是正常的，在 DeerFlow sandbox 中会存在）")
else:
    print(f"✅ water-situation/SKILL.md 存在")

# 测试 6: 本地实际路径（开发环境）
print("\n[6] 开发环境实际路径对比")
repo_root = Path("/opt/git/water-resources-skills/skills")
if repo_root.exists():
    actual_lib = repo_root / 'lib'
    actual_shared = repo_root / 'shared'
    print(f"实际仓库路径:")
    print(f"  lib/  → {actual_lib} {'✅' if actual_lib.exists() else '❌'}")
    print(f"  shared/ → {actual_shared} {'✅' if actual_shared.exists() else '❌'}")

    if actual_lib.exists() and actual_shared.exists():
        print(f"\n✅ 仓库本地路径有效，可在开发环境使用")
        print(f"   临时测试: WATER_RESOURCES_ROOT=/opt/git/water-resources-skills/skills python3 scripts/deerflow_verify_paths.py")

print("\n" + "=" * 70)
print("✅ 快速测试完成")
print("=" * 70)
print(f"""
说明:
  - /mnt/skills 是 DeerFlow 虚拟路径，仅在 sandbox 内有效
  - 实际映射到: /opt/git/water-resources-skills/skills
  - 标准导入片段在 DeerFlow 中应能正常工作

下一步:
  1. 在 DeerFlow Web UI 中测试查询
  2. 或运行完整验证（需要数据库密码）:
     cd /opt/git/water-resources-skills/skills
     WATER_RESOURCES_ROOT=/opt/git/water-resources-skills/skills python3 scripts/deerflow_verify_paths.py
""")

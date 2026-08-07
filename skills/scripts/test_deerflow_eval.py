#!/usr/bin/env python3
"""简化版 eval：直接调用 LLM API（不通过 DeerFlow client）"""

import sys
import os
sys.path.insert(0, '/opt/git/water-resources-skills/skills/lib')
sys.path.insert(0, '/opt/git/water-resources-skills/skills')

from db import query
from pathlib import Path
import json

# 加载 test cases
def load_test_cases():
    """加载测试用例"""
    md_path = '/opt/git/water-resources-skills/skills/docs/test-cases-with-sql.md'
    with open(md_path) as f:
        content = f.read()

    cases = []
    lines = content.split('\n')
    skill = level = ''
    for i, line in enumerate(lines):
        line = line.strip()
        import re
        skill_match = re.match(r"^##\s+\d+\.\s+([a-z][\w-]+)", line)
        if skill_match:
            skill = skill_match.group(1)
            continue
        level_match = re.match(r"^###\s+(L[123])", line)
        if level_match:
            level = level_match.group(1)
            continue
        q_match = re.match(r"^\*\*Q(\d+):\*\*\s*(.+)", line)
        if q_match and skill and level:
            q_num = int(q_match.group(1))
            question = q_match.group(2).strip()
            cases.append({'index': len(cases)+1, 'skill': skill, 'level': level, 'question': question})
    return cases

# 模拟 LLM 调用（这里只验证 skill 文件存在和数据库连接）
def test_skill_availability():
    """测试 skill 可用性"""
    print("=" * 60)
    print("DeerFlow Eval 可行性验证")
    print("=" * 60)

    # 1. 检查 skill 文件
    print("\n1. 检查 Skill 文件...")
    skill_root = Path('/opt/git/water-resources-skills/skills')
    skills = ['water-situation', 'rainfall', 'water-quality', 'water-forecast', 'gate-pump-operation', 'water-warning']
    for skill in skills:
        skill_file = skill_root / skill / 'SKILL.md'
        if skill_file.exists():
            print(f"   ✅ {skill}/SKILL.md")
        else:
            print(f"   ❌ {skill}/SKILL.md 缺失")

    # 2. 检查数据库连接
    print("\n2. 检查数据库连接...")
    try:
        result = query("SELECT 1 as test")
        print(f"   ✅ 数据库连接成功: {result}")
    except Exception as e:
        print(f"   ❌ 数据库连接失败: {e}")

    # 3. 加载测试用例
    print("\n3. 加载测试用例...")
    cases = load_test_cases()
    print(f"   ✅ 加载 {len(cases)} 个测试用例")

    # 4. 按 skill/level 统计
    from collections import Counter
    skill_count = Counter(c['skill'] for c in cases)
    level_count = Counter(c['level'] for c in cases)
    print("\n   按 Skill:")
    for skill, count in sorted(skill_count.items()):
        print(f"     {skill}: {count}")
    print("\n   按难度:")
    for level, count in sorted(level_count.items()):
        print(f"     {level}: {count}")

    # 5. 输出第一个测试用例（用于验证）
    print("\n4. 示例测试用例（Q1）:")
    print(f"   Skill: {cases[0]['skill']}")
    print(f"   Level: {cases[0]['level']}")
    print(f"   Question: {cases[0]['question'][:80]}...")

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

    return cases

if __name__ == "__main__":
    cases = test_skill_availability()

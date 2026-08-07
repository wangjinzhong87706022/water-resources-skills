#!/usr/bin/env python3
"""
提取口径信息：从现有文档提取 S3/S5/S6 素材
"""

import re
from pathlib import Path
import json

def extract_section(content: str, header: str) -> str:
    """提取 markdown 章节"""
    pattern = rf'## {header}\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

def extract_schema_tables(schema_content: str) -> dict:
    """提取 schema.md 中的表信息"""
    tables = {}
    # 匹配 ## 表名 — 描述
    table_headers = re.findall(r'^## ([^\n]+?)(?: — ([^\n]+))?$', schema_content, re.MULTILINE)
    
    for table_name, description in table_headers:
        tables[table_name] = {'description': description}
        
    return tables

def extract_pitfalls(skill_md: str) -> list:
    """提取 SKILL.md Pitfalls 中的关键信息"""
    pitfalls = []
    
    # 提取 ## Pitfalls 章节
    pitfalls_section = extract_section(skill_md, 'Pitfalls')
    if not pitfalls_section:
        return pitfalls
    
    # 提取要点（以 - 或 ** 开头的行）
    lines = pitfalls_section.split('\n')
    current_topic = None
    for line in lines:
        line = line.strip()
        
        # 检测主题（** 开头或 ## ### 开头）
        topic_match = re.match(r'\*\*(.+?):?\*\*|^#{1,4}\s+(.+)', line)
        if topic_match:
            current_topic = topic_match.group(1) if topic_match.group(1) else topic_match.group(2)
            continue
        
        # 检测要点
        if line.startswith('- ') or line.startswith('* '):
            point = line[2:].strip()
            if current_topic and point:
                pitfalls.append({'topic': current_topic, 'point': point})
    
    return pitfalls

def extract_sql_patterns(few_shots: str) -> list:
    """提取 few_shots.md 中的 SQL 模式"""
    patterns = []
    
    # 提取 ```sql ... ``` 块
    sql_blocks = re.findall(r'```sql\s*\n(.*?)\n```', few_shots, re.DOTALL | re.IGNORECASE)
    
    for sql in sql_blocks:
        # 提取 FROM/JOIN 的表名
        tables = re.findall(r'(?:FROM|JOIN)\s+([\w.]+)', sql, re.IGNORECASE)
        # 提取 WHERE 条件
        where_match = re.search(r'WHERE\s+(.+?)(?:\nORDER|\nLIMIT|\Z)', sql, re.DOTALL | re.IGNORECASE)
        where = where_match.group(1).strip() if where_match else ""
        
        patterns.append({
            'tables': tables,
            'where_conditions': where,
            'sql_preview': sql[:100] + '...' if len(sql) > 100 else sql
        })
    
    return patterns

def main():
    skill_root = Path('/opt/git/water-resources-skills/skills')
    skills = ['water-situation', 'rainfall', 'water-quality', 'water-forecast', 'gate-pump-operation', 'water-warning']
    
    print("=" * 60)
    print("提取口径信息")
    print("=" * 60)
    
    for skill in skills:
        print(f"\n{'='*60}")
        print(f"Skill: {skill}")
        print(f"{'='*60}")
        
        skill_dir = skill_root / skill
        
        # 1. 读取 SKILL.md
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.exists():
            print(f"  ❌ SKILL.md 不存在")
            continue
        
        skill_content = skill_md.read_text()
        
        # 提取 Pitfalls
        pitfalls = extract_pitfalls(skill_content)
        print(f"\nPitfalls ({len(pitfalls)} 条):")
        for p in pitfalls[:5]:  # 只显示前 5 条
            print(f"  - [{p['topic']}] {p['point'][:80]}")
        
        # 2. 读取 schema.md
        schema_md = skill_dir / 'references' / 'schema.md'
        if schema_md.exists():
            schema_content = schema_md.read_text()
            tables = extract_schema_tables(schema_content)
            print(f"\nSchema 表 ({len(tables)} 张):")
            for table_name, info in tables.items():
                print(f"  - {table_name}: {info['description']}")
            
            # 3. 检测分区表
            partitioned_tables = []
            for table_name in tables.keys():
                # 简单检测：如果 schema 中提到 "RANGE" 或 "PARTITION"
                if re.search(r'RANGE|PARTITION|分区', schema_content, re.IGNORECASE):
                    if table_name.lower() in schema_content.lower():
                        partitioned_tables.append(table_name)
            
            if partitioned_tables:
                print(f"\n  分区表: {', '.join(partitioned_tables)}")
        else:
            print(f"  ❌ references/schema.md 不存在")
        
        # 3. 读取 few_shots.md
        few_shots_md = skill_dir / 'references' / 'few_shots.md'
        if few_shots_md.exists():
            few_shots_content = few_shots_md.read_text()
            patterns = extract_sql_patterns(few_shots_content)
            print(f"\nSQL 模式 ({len(patterns)} 个):")
            for p in patterns[:3]:
                print(f"  - 表: {p['tables']}")
                print(f"    WHERE: {p['where_conditions'][:60]}...")
        
        print()

if __name__ == "__main__":
    main()

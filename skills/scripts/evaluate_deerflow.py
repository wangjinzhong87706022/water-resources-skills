#!/usr/bin/env python3
"""
DeerFlow Eval Harness — 直接调用 LLM API（跳过 DeerFlow client 的 MCP 问题）

原理：
  1. 从 config.yaml 读取模型配置（base_url、api_key、model）
  2. 加载 Skill 文件内容
  3. 构造 system prompt（skill 指令）
  4. 调用 OpenAI-compatible API（与 hermes 相同路径）
  5. 评估响应（复用 evaluate_skills.py 的评分逻辑）

优势：
  - 不需要 DeerFlow Gateway 服务
  - 不需要解决 MCP session 初始化问题
  - 直接测试 skill + LLM 的核心能力
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml
from openai import OpenAI

# 加载 test case 解析逻辑
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.evaluate_skills import parse_test_cases

# ============================================================
# DeerFlow 配置
# ============================================================

def load_deerflow_config(config_path: str = '/opt/git/deer-flow/config.yaml') -> dict:
    """加载 DeerFlow 配置"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    models = config.get('models', [])
    if not models:
        raise ValueError("配置中无模型定义")

    model = models[0]
    return {
        'model': model['model'],
        'base_url': model['base_url'],
        'api_key': model.get('api_key', 'sk-no-key-required'),
        'temperature': model.get('temperature', 0.4),
        'max_tokens': model.get('max_tokens', 8192),
        'request_timeout': model.get('request_timeout', 600),
    }

def load_skill_content(skill_name: str, skills_root: str = '/opt/git/water-resources-skills/skills') -> str:
    """加载 Skill 文件内容"""
    skill_path = Path(skills_root) / skill_name / 'SKILL.md'
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill 文件不存在: {skill_path}")
    return skill_path.read_text()

# ============================================================
# LLM 调用
# ============================================================

def call_llm(
    config: dict,
    system_prompt: str,
    user_message: str,
    timeout: int = 600
) -> str:
    """调用 LLM API"""
    client = OpenAI(
        api_key=config['api_key'],
        base_url=config['base_url'],
        timeout=config['request_timeout'],
    )

    response = client.chat.completions.create(
        model=config['model'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=config.get('temperature', 0.4),
        max_tokens=config.get('max_tokens', 8192),
    )

    return response.choices[0].message.content

# ============================================================
# 评分逻辑
# ============================================================

def normalize_sql(sql: str) -> str:
    """标准化 SQL 用于比较 —— 只比查询结构（表/列/谓词），忽略别名/字面量/限定前缀。

    设计理由：旧版只去引号别名，导致「英文别名 b.stnm AS station_name」与
    期望「中文别名 stnm AS '测站名称'」相似度恒为 0.05，把功能正确的 SQL 判成低分。
    新版先去所有 AS 别名，再归一字面量、去表/列限定前缀、规整 LIKE→=，
    使相似度反映查询语义而非书写风格。
    """
    s = sql.strip().rstrip(";").strip().lower()
    # 1. 先去 AS 别名（此时引号/裸词还在，能精确匹配）
    s = re.sub(r"\bas\s+'[^']*'", "", s)
    s = re.sub(r'\bas\s+"[^"]*"', "", s)
    s = re.sub(r"\bas\s+`[^`]*`", "", s)
    s = re.sub(r"\bas\s+\w+", "", s)
    # 2. 字符串/数字字面量 → ?
    s = re.sub(r"'[^']*'", "?", s)
    s = re.sub(r"\b\d+\.?\d*\b", "?", s)
    # 3. 去表/列限定前缀（b.stnm → stnm, sl323.st_stbprp_b → st_stbprp_b）
    s = re.sub(r"\b\w+\.", "", s)
    # 4. LIKE → =（均为过滤谓词，相似度比较时视作同类）
    s = re.sub(r"\blike\b", "=", s)
    # 5. 折叠空白
    s = re.sub(r"\s+", " ", s).strip()
    return s

def sql_similarity(sql1: str, sql2: str) -> float:
    """计算 SQL 相似度"""
    n1 = normalize_sql(sql1)
    n2 = normalize_sql(sql2)
    if not n1 or not n2:
        return 0.0
    words1 = set(n1.split())
    words2 = set(n2.split())
    intersection = words1 & words2
    union = words1 | words2
    if not union:
        return 0.0
    return len(intersection) / len(union)

def check_sql_safety(sql: str) -> dict:
    """检查 SQL 安全"""
    issues = []
    sql_upper = sql.upper().strip()

    if not any(sql_upper.startswith(kw) for kw in ["SELECT", "SHOW", "DESCRIBE"]):
        issues.append("非只读语句")

    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]
    for kw in dangerous:
        if re.search(rf"\b{kw}\b", sql_upper):
            issues.append(f"包含危险操作: {kw}")

    if "FROM" in sql_upper and "WHERE" not in sql_upper and "JOIN" not in sql_upper:
        issues.append("无 WHERE 条件")

    if "LIMIT" not in sql_upper and "COUNT" not in sql_upper:
        issues.append("无 LIMIT")

    return {"safe": len(issues) == 0, "issues": issues}

def extract_sql(response: str) -> str:
    """从响应中提取 SQL（支持 Python 脚本中的 SQL 字符串）"""
    # 1. 匹配 ```sql ... ```
    match = re.search(r"```sql\s*\n(.*?)\n```", response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 2. 匹配 ```python ... ``` 中的 SQL 字符串
    match = re.search(r"```python\s*\n(.*?)\n```", response, re.DOTALL)
    if match:
        python_code = match.group(1)
        # 提取 sql = """...""" 或 sql = '...'（优先匹配三引号）
        sql_match = re.search(r'sql\s*=\s*"""(.*?)"""', python_code, re.DOTALL | re.IGNORECASE)
        if not sql_match:
            # 尝试单引号
            sql_match = re.search(r"sql\s*=\s*'''(.*?)'''", python_code, re.DOTALL | re.IGNORECASE)
        if not sql_match:
            # 尝试双引号
            sql_match = re.search(r'sql\s*=\s*"(.*?)"', python_code, re.DOTALL | re.IGNORECASE)
        if not sql_match:
            # 尝试单引号
            sql_match = re.search(r"sql\s*=\s*'(.*?)'", python_code, re.DOTALL | re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
            return sql

    # 3. 匹配任意 ```...```
    match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if content.upper().startswith("SELECT") or content.upper().startswith("WITH"):
            return content

    # 4. 匹配 sql = """...""" 或 sql = '...'（无代码块）
    match = re.search(r'sql\s*=\s*[\"\"\']+(.*?)[\"\"\']+', response, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
        sql = re.sub(r'^[\"\'\n]+|[\"\'\n]+$', '', sql)
        return sql.strip()

    # 5. 匹配直接的 SELECT 语句
    match = re.search(r"(SELECT\s+.*?;)", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return ""

def execute_safe(sql: str, timeout: int = 20) -> tuple[bool, list, str]:
    """只读执行 SQL（SELECT-only），返回 (ok, rows, error)。失败不抛异常。

    通过 skills/lib/db.py 复用连接配置（host/.env 密码回退）。
    只放行 SELECT/SHOW/DESCRIBE/EXPLAIN/WITH，保证只读安全。
    """
    if not sql:
        return False, [], "空 SQL"
    head = sql.strip().lstrip("(").upper()
    if not head.startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH")):
        return False, [], "非只读语句"
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
        from db import query  # 复用 .env 密码回退 + 连接配置
        rows = query(sql, timeout=timeout)
        return True, rows, ""
    except Exception as e:
        return False, [], str(e)[:120]


def _value_bag(rows: list) -> "Counter":
    """把结果集所有单元格值压成 Counter（小写字符串；忽略 None/空）。"""
    from collections import Counter
    bag: Counter = Counter()
    for row in rows:
        if isinstance(row, dict):
            for v in row.values():
                if v is None:
                    continue
                s = str(v).strip().lower()
                if s and s not in ("none", "null"):
                    bag[s] += 1
    return bag


def compute_result_correctness(actual_sql: str, expected_sql: str) -> tuple[Optional[float], dict]:
    """执行两条 SQL 并比对结果集，返回 (0-1 分 或 None, 详情)。

    设计理由（eval-v2）：旧评分只看文本，把「SQL 正确但用英文别名」误判为低分
    （Q2 假阴性）。本维度真去库上跑，按「值集合 F1（忽略列名/行序/别名）」
    衡量答案正确性。

    返回 None 的情形（不可测量 → 中性，不参与计分）：
      - actual_sql 为空（提取失败）：无法判断对错，不能当错处理
    返回数值的情形：
      - 期望 SQL 跑不了（测试集自身缺陷）→ 实际能执行给 0.6 基础分，否则 0
      - 实际 SQL 执行失败 → 0.0（真错）
      - 两者皆空 → 1.0；期望空/实际非空 → 0.3
      - 否则取值集合 F1（recall 为主，precision 防爆）

    注意：返回值在 score_case 中作「只抬不压」的 floor-lift 使用——因为期望 SQL
    并非绝对真值（如 Q22 期望用 CURDATE() 查无数据的月份，实际才是对的），
    低正确性不压分，仅高正确性抬分。
    """
    if not actual_sql or not actual_sql.strip():
        return None, {"reason": "actual_sql 为空（提取失败），不可测量"}
    a_ok, a_rows, a_err = execute_safe(actual_sql)
    e_ok, e_rows, e_err = execute_safe(expected_sql)
    detail = {
        "actual_rows": len(a_rows), "expected_rows": len(e_rows),
        "actual_err": a_err, "expected_err": e_err,
    }
    if not e_ok:
        return (0.6 if a_ok else 0.0), detail
    if not a_ok:
        return 0.0, detail
    a_bag = _value_bag(a_rows)
    e_bag = _value_bag(e_rows)
    if not e_bag and not a_bag:
        return 1.0, detail
    if not e_bag:
        return 0.3, detail
    if not a_bag:
        return 0.1, detail
    inter = sum((a_bag & e_bag).values())
    p = inter / sum(a_bag.values()) if sum(a_bag.values()) else 0.0
    r = inter / sum(e_bag.values())
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    # recall 为主（是否返回了被问的数据），precision 仅在严重偏低时下调
    score = r if p >= 0.1 else round(0.5 * r, 2)
    return round(max(f1, score), 2), detail


def score_case(case, actual_sql: str, response: str,
               result_correctness: Optional[float] = None) -> tuple[float, dict]:
    """评分。result_correctness 非空时启用 eval-v2 五维（结果正确性主导）。"""
    scores = {}

    # 维度 1: 有效响应
    has_valid_response = 0.0
    if response and not response.startswith("[ERROR") and len(response) > 30:
        has_valid_response = 1.0
    scores['has_valid_response'] = has_valid_response

    # 维度 2: 领域数据
    skill_keywords = {
        'water-situation': ['水位', '测站', '河流', '水情', '水文'],
        'rainfall': ['降雨', '雨量', '降水', '雨站', 'mm'],
        'water-quality': ['水质', '溶解氧', 'CODMn', '氨氮', 'pH'],
        'water-forecast': ['预测', '预报', '任务', '模型', '水位'],
        'gate-pump-operation': ['闸', '泵', '开度', '流量', '启闭'],
        'water-warning': ['预警', '超警戒', '超保证', '防洪'],
    }
    keywords = skill_keywords.get(case.skill, ['数据', '查询'])
    keyword_hits = sum(1 for kw in keywords if kw in response)
    has_domain_data = min(1.0, keyword_hits / 3.0)
    scores['has_domain_data'] = round(has_domain_data, 2)

    # 维度 3: 数值数据
    numbers = re.findall(r"\d+\.?\d*", response)
    has_numeric_data = 1.0 if len(numbers) >= 3 else 0.5 if len(numbers) >= 1 else 0.0
    scores['has_numeric_data'] = has_numeric_data

    # 维度 4: SQL 相似度
    if actual_sql and case.expected_sql:
        similarity = sql_similarity(actual_sql, case.expected_sql)
        sim_score = 1.0 if similarity >= 0.6 else 0.7 if similarity >= 0.4 else 0.4 if similarity >= 0.2 else 0.2
    else:
        sim_score = 0.7 if len(response) > 200 else 0.4 if len(response) > 50 else 0.1
    scores['response_quality'] = round(sim_score, 2)

    # 维度 5: SQL 安全
    sql_safety = check_sql_safety(actual_sql) if actual_sql else {"safe": True, "issues": []}
    safe_score = 1.0 if sql_safety['safe'] else 0.5 if len(sql_safety['issues']) <= 1 else 0.0
    scores['sql_safe'] = safe_score
    scores['safety_issues'] = sql_safety['issues']

    # 总分
    # eval-v1 基线（四维文本启发式，已用修复版 normalize）
    v1_total = round(
        has_valid_response * 0.20 + has_domain_data * 0.30
        + has_numeric_data * 0.25 + sim_score * 0.25, 2
    )
    if result_correctness is not None:
        # eval-v2：结果正确性作 floor-lift（只抬不压）。
        # 理由：期望 SQL 非绝对真值（如 Q22 期望查无数据月份），低正确性可能
        # 是参考答案本身陈旧，故仅在正确性高时抬分，永不低于 v1 基线。
        scores['result_correctness'] = result_correctness
        blended = round(0.5 * v1_total + 0.5 * result_correctness, 2)
        total = max(v1_total, blended)
    else:
        # actual_sql 为空（不可测量）→ 中性，沿用 v1
        total = v1_total

    return total, scores

# ============================================================
# 报告生成
# ============================================================

def generate_report(results: List, output_dir: str):
    """生成评估报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON 报告（手动构造 dict，避免 asdict 问题）
    json_path = os.path.join(output_dir, f"deerflow_eval_{timestamp}.json")
    results_data = []
    for r in results:
        results_data.append({
            'index': r.index,
            'skill': r.skill,
            'level': r.level,
            'question': r.question,
            'expected_sql': r.expected_sql,
            'actual_response': r.actual_response,
            'actual_sql': r.actual_sql,
            'scores': r.scores,
            'total_score': r.total_score,
            'duration_sec': r.duration_sec,
            'error': r.error,
            'attribution': r.attribution,
        })

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'meta': {'timestamp': timestamp, 'total_cases': len(results)},
            'results': results_data,
        }, f, ensure_ascii=False, indent=2)

    # Markdown 报告
    md_path = os.path.join(output_dir, f"deerflow_report_{timestamp}.md")
    scores = [r.total_score for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    pass_rate = sum(1 for s in scores if s >= 0.6) / len(scores) if scores else 0

    lines = [
        f"# DeerFlow Eval 报告",
        f"",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 测试用例: {len(results)}",
        f"",
        f"## 总体评分",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| **平均分** | {avg_score:.2f} |",
        f"| **通过率 (≥0.6)** | {pass_rate:.1%} |",
        f"",
    ]

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"\n✅ 报告已生成:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")

# ============================================================
# 主流程
# ============================================================

def run_eval(
    skill_names: List[str],
    output_dir: str,
    test_cases_path: str = '/opt/git/water-resources-skills/skills/docs/test-cases-with-sql.md',
    timeout: int = 600,
    max_cases: int = 0,
):
    """运行 eval"""
    os.makedirs(output_dir, exist_ok=True)

    # 1. 加载配置
    print("\n1. 加载 DeerFlow 配置...")
    config = load_deerflow_config()
    print(f"   模型: {config['model']}")
    print(f"   Base URL: {config['base_url']}")

    # 2. 加载测试用例
    print("\n2. 加载测试用例...")
    all_cases = parse_test_cases(test_cases_path)
    print(f"   总计加载: {len(all_cases)} 个用例")

    if skill_names:
        all_cases = [c for c in all_cases if c.skill in skill_names]
        print(f"   过滤后: {len(all_cases)} 个 ({', '.join(skill_names)})")

    if max_cases > 0:
        all_cases = all_cases[:max_cases]
        print(f"   限制: 前 {max_cases} 题")

    if not all_cases:
        print("   ❌ 无测试用例，退出")
        return

    # 3. 执行评估
    results = []
    for i, case in enumerate(all_cases):
        print(f"\n[{i+1}/{len(all_cases)}] Q{case.index} [{case.skill}/{case.level}] — {case.question[:60]}")

        try:
            skill_content = load_skill_content(case.skill)

            start = time.time()
            response = call_llm(config, skill_content, case.question, timeout=timeout)
            duration = time.time() - start

            actual_sql = extract_sql(response)
            rc_score, rc_detail = compute_result_correctness(actual_sql, case.expected_sql)
            total_score, scores = score_case(case, actual_sql, response, result_correctness=rc_score)

            result = type('EvalResult', (), {})()
            result.index = case.index
            result.skill = case.skill
            result.level = case.level
            result.question = case.question
            result.expected_sql = case.expected_sql
            result.actual_response = response
            result.actual_sql = actual_sql
            result.scores = scores
            result.total_score = total_score
            result.duration_sec = round(duration, 2)
            result.error = ""
            result.attribution = {"result_correctness": rc_score, "exec_detail": rc_detail}

            rc_disp = f"{rc_score:.2f}" if rc_score is not None else " N/A"
            print(f"   → 总分={total_score:.2f} | SQL:{'Yes' if actual_sql else 'No'} | 正确性={rc_disp} | {duration:.1f}s")

        except Exception as e:
            import traceback
            result = type('EvalResult', (), {})()
            result.index = case.index
            result.skill = case.skill
            result.level = case.level
            result.question = case.question
            result.expected_sql = case.expected_sql
            result.actual_response = ""
            result.actual_sql = ""
            result.scores = {}
            result.total_score = 0.0
            result.duration_sec = 0.0
            result.error = str(e)[:200]
            result.attribution = {}
            print(f"   ❌ 错误: {e}")
            traceback.print_exc()

        results.append(result)

    # 4. 生成报告
    generate_report(results, output_dir)

def main():
    parser = argparse.ArgumentParser(description="DeerFlow Eval Harness")
    parser.add_argument('--skills', nargs='+', help='要评估的 skill 列表（不指定则全部）')
    parser.add_argument('--output', default='reports/deerflow_eval', help='报告输出目录')
    parser.add_argument('--timeout', type=int, default=600, help='单题超时（秒）')
    parser.add_argument('--max-cases', type=int, default=0, help='最多执行题数（0=全部）')
    parser.add_argument('--range', help='题号范围（如 1-10）')
    args = parser.parse_args()

    print("=" * 60)
    print("DeerFlow Eval Harness")
    print("=" * 60)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"{args.output}_{timestamp}"

    run_eval(
        skill_names=args.skills,  # None 表示全部
        output_dir=output_dir,
        timeout=args.timeout,
        max_cases=args.max_cases,
    )

if __name__ == "__main__":
    main()

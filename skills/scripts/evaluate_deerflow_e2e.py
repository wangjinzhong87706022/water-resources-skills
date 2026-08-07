#!/usr/bin/env python3
"""
DeerFlow 端到端评测脚本 v2

用法：
  # 全量 98 题（单技能）
  python evaluate_deerflow_e2e.py --skill water-situation

  # 指定题号范围
  python evaluate_deerflow_e2e.py --skill water-situation --range 1-10

  # 所有技能全量跑
  python evaluate_deerflow_e2e.py --all-skills

  # Dry run（不执行，只解析）
  python evaluate_deerflow_e2e.py --skill water-situation --dry-run
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional, Tuple

# ============================================================
# 数据模型
# ============================================================

@dataclass
class TestCase:
    """单个测试用例"""
    index: int
    skill: str
    level: str
    question: str
    expected_sql: str
    question_num: int = 0

@dataclass
class EvalResult:
    """单个测试用例的评估结果"""
    index: int
    skill: str
    level: str
    question: str
    expected_sql: str
    actual_response: str = ""
    extracted_code: str = ""  # SQL 或 Python 脚本
    code_type: str = ""  # "sql" | "python" | "none"
    execution_result: dict = field(default_factory=dict)
    execution_error: str = ""
    scores: dict = field(default_factory=dict)
    total_score: float = 0.0
    duration_sec: float = 0.0
    error: str = ""
    completed: bool = True

# ============================================================
# 测试用例解析
# ============================================================

def parse_test_cases(md_path: str) -> list[TestCase]:
    """从 markdown 文件解析测试用例"""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    cases = []
    global_idx = 0
    current_skill = ""
    current_level = ""

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 匹配 skill 标题: ## 1. water-situation（实时水位查询）
        skill_match = re.match(r"^##\s+\d+\.\s+([a-z][\w-]+)", line)
        if skill_match:
            current_skill = skill_match.group(1)
            current_level = ""
            i += 1
            continue

        # 匹配难度标题: ### L1 — 简单单表查询
        level_match = re.match(r"^###\s+(L[123])", line)
        if level_match:
            current_level = level_match.group(1)
            i += 1
            continue

        # 匹配问题: **Q1:** 古运河有哪些水位测站？
        q_match = re.match(r"^\*\*Q(\d+):\*\*\s*(.+)", line)
        if q_match and current_skill and current_level:
            q_num = int(q_match.group(1))
            question = q_match.group(2).strip()

            # 向后查找 SQL 块
            expected_sql = ""
            j = i + 1
            while j < len(lines):
                if lines[j].strip().startswith("```sql"):
                    sql_lines = []
                    j += 1
                    while j < len(lines) and not lines[j].strip().startswith("```"):
                        sql_lines.append(lines[j])
                        j += 1
                    expected_sql = "\n".join(sql_lines).strip()
                    break
                j += 1

            if expected_sql:
                global_idx += 1
                cases.append(TestCase(
                    index=global_idx,
                    skill=current_skill,
                    level=current_level,
                    question=question,
                    expected_sql=expected_sql,
                    question_num=q_num,
                ))

        i += 1

    return cases

# ============================================================
# LLM 调用（复用 evaluate_deerflow.py 的逻辑）
# ============================================================

def load_deerflow_config(config_path: str = '/opt/git/deer-flow/config.yaml') -> dict:
    """加载 DeerFlow 配置"""
    import yaml
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

def call_llm(config: dict, system_prompt: str, user_message: str, timeout: int = 600) -> str:
    """调用 LLM API（直接 OpenAI 兼容）"""
    from openai import OpenAI

    client = OpenAI(
        api_key=config['api_key'],
        base_url=config['base_url'],
        timeout=timeout,
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
# 输出解析（提取 SQL 或 Python 脚本）
# ============================================================

def extract_code_from_response(response: str) -> Tuple[str, str]:
    """从 LLM 回答中提取 SQL 或 Python 代码

    Returns:
        (code, type) 其中 type 为 "sql" / "python" / "none"
    """
    # 优先匹配 ```sql ... ``` 块
    match = re.search(r"```sql\s*\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), "sql"

    # 匹配 ```python ... ``` 块
    match = re.search(r"```python\s*\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), "python"

    # 匹配 ```...``` 块（无语言标记，内容可能是 SQL 或 Python）
    match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
    if match:
        content = match.group(1).strip()
        # 判断是 SQL 还是 Python
        if re.match(r"^(SELECT|SHOW|DESCRIBE|WITH)\b", content, re.IGNORECASE):
            return content, "sql"
        if re.match(r"^(import |from |def |class |if __name__|#!)", content, re.IGNORECASE):
            return content, "python"

    # 匹配直接出现的 SQL（以 SELECT 开头，直到分号或换行）
    match = re.search(r"(SELECT\s+.*?)(?:;|\n\s*\n)", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), "sql"

    # 匹配 Python 脚本（有 import 或 from db import）
    if "from db import" in response or "import pymysql" in response:
        lines = response.split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if re.match(r"^(import |from )", line.strip()):
                in_code = True
            if in_code:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines).strip(), "python"

    return "", "none"

# ============================================================
# 执行提取的代码
# ============================================================

def execute_sql_safe(sql: str, timeout: int = 30, allow_full_scan: bool = False) -> dict:
    """执行 SQL，返回结果"""
    try:
        skills_root = os.environ.get("WATER_RESOURCES_ROOT", "/opt/git/water-resources-skills/skills")
        sys.path.insert(0, os.path.join(skills_root, "lib"))
        from db import query

        sql_clean = sql.strip().rstrip(";").strip()
        if not sql_clean.upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
            return {"ok": False, "error": "Only SELECT/SHOW/DESCRIBE/EXPLAIN allowed", "rows": []}

        rows = query(sql_clean, timeout=timeout, allow_full_scan=allow_full_scan)
        return {"ok": True, "rows": rows, "row_count": len(rows), "error": ""}
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}

def execute_python_safe(code: str, timeout: int = 30) -> dict:
    """执行 Python 脚本，返回结果"""
    try:
        import tempfile
        import subprocess as sp

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name

        skills_root = os.environ.get("WATER_RESOURCES_ROOT", "/opt/git/water-resources-skills/skills")
        env = {**os.environ, "WATER_RESOURCES_ROOT": skills_root, "PYTHONPATH": os.path.join(skills_root, "lib")}

        result = sp.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        os.unlink(tmp_path)

        output = result.stdout.strip()
        error = result.stderr.strip() if result.returncode != 0 else ""

        return {
            "ok": result.returncode == 0,
            "stdout": output,
            "stderr": error,
            "returncode": result.returncode,
        }
    except sp.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout after {timeout}s", "returncode": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}

# ============================================================
# 结果比较
# ============================================================

def value_bag(rows: list[dict]) -> dict:
    """从结果行提取值 bag（无序集合，保留原 str 形式供 F1 路径使用）"""
    from collections import Counter
    bag = Counter()
    for row in rows:
        for k, v in row.items():
            if v is not None:
                bag[str(v)] += 1
    return dict(bag)

# ============================================================
# 归一化值匹配（修 result_quality 系统性低估）
#
# 旧逻辑：value_bag 存 str(Decimal('4.7035670'))="4.7035670"，再用
# "4.7035670" in stdout 做子串匹配 → Agent 报 "4.74m" 必失配。
# 三类系统性失配：(1) 单位后缀(m/mg/L/m³/s) (2) 小数精度(golden 无 ROUND)
# (3) 日期重排(2026-07-02 → 7月2日)。归一化后用数值近邻容差 + 文本子串。
# ============================================================

_DATE_STR_RE = re.compile(r'^\d{4}[-/]\d{1,2}([-/]\d{1,2})?$')
# 数值 token：匹配 "4.74"、"222.9"、"-0.5"；不吞日期里的 "-"（要求左侧非数字）
_NUM_TOKEN_RE = re.compile(r'(?<![\w.])-?\d+\.?\d*(?:[eE][-+]?\d+)?')

def _is_date_like(v) -> bool:
    """日期/datetime 对象，或 'YYYY-MM-DD'/'YYYY-MM' 形式字符串 → 视为键，不计入匹配"""
    if isinstance(v, (datetime, date)):
        return True
    if isinstance(v, str):
        s = v.strip()
        if _DATE_STR_RE.match(s):
            return True
    return False

def _to_float(v):
    """能转 float 就转，否则 None"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        m = _NUM_TOKEN_RE.fullmatch(s)
        if m:
            try:
                return float(s)
            except ValueError:
                return None
    return None

def _split_values(rows: list[dict]) -> tuple[list[float], list[str]]:
    """把结果行拆成 (数值列表, 非日期文本列表)。日期类键被丢弃。"""
    nums: list[float] = []
    texts: list[str] = []
    for row in rows:
        for k, v in row.items():
            if v is None or _is_date_like(v):
                continue
            f = _to_float(v)
            if f is not None:
                nums.append(f)
            elif isinstance(v, str) and v.strip():
                texts.append(v.strip())
            # 其它类型（dict/list）跳过
    return nums, texts

def _extract_stdout_numbers(stdout: str) -> list[float]:
    """从答案文本里抽所有数值 token（自动剥离 'm'/'mg/L' 等单位后缀）"""
    out = []
    for m in _NUM_TOKEN_RE.finditer(stdout):
        try:
            out.append(float(m.group()))
        except ValueError:
            pass
    return out

def _num_hit(expected: float, stdout_nums: list[float]) -> bool:
    """数值近邻匹配：容差 = max(0.02 绝对, 0.5% 相对)。
    选小容差以保留区分度（4.70 与 4.74 不会误判为同一个值）。"""
    tol = max(0.02, abs(expected) * 0.005)
    return any(abs(n - expected) <= tol for n in stdout_nums)

def stdout_recall(stdout: str, expected_rows: list[dict]) -> dict:
    """计算 expected SQL 结果值在 agent stdout/答案文本中的召回率（归一化匹配）。

    - 数值：近邻容差匹配（解决精度四舍五入 + 单位后缀失配）
    - 文本（站名等）：子串匹配
    - 日期键：不计入（Agent 重排日期不应扣分）
    """
    exp_nums, exp_texts = _split_values(expected_rows)

    if not exp_nums and not exp_texts:
        return {"match_type": "stdout_no_expected_values", "score": 0.3,
                "detail": "Expected SQL returned no comparable values"}

    stdout_nums = _extract_stdout_numbers(stdout)

    # 数值召回
    num_hits = sum(1 for e in exp_nums if _num_hit(e, stdout_nums)) if exp_nums else 0
    num_recall = (num_hits / len(exp_nums)) if exp_nums else None

    # 文本召回（站名等）
    text_hits = sum(1 for t in exp_texts if t and len(t) >= 2 and t in stdout)
    text_recall = (text_hits / len(exp_texts)) if exp_texts else None

    recalls = [r for r in (num_recall, text_recall) if r is not None]
    score = sum(recalls) / len(recalls) if recalls else 0.0

    total = len(exp_nums) + len(exp_texts)
    hits = num_hits + text_hits
    detail = (f"stdout matched {hits}/{total} "
              f"(numeric {num_hits}/{len(exp_nums) if exp_nums else 0}, "
              f"text {text_hits}/{len(exp_texts) if exp_texts else 0})")
    return {"match_type": "stdout_recall", "score": round(score, 3),
            "detail": detail}

def compare_results(actual: dict, expected_sql: str) -> dict:
    """比较执行结果与预期 SQL 的结果"""
    result = {"match_type": "unknown", "score": 0.0, "detail": ""}

    # Python 结果只有 stdout 文本，用 expected 值召回来评分
    if not actual.get("rows") and actual.get("stdout"):
        expected_exec = execute_sql_safe(expected_sql, allow_full_scan=True)
        if expected_exec["ok"]:
            return stdout_recall(actual["stdout"], expected_exec["rows"])
        # expected SQL 不可执行，只要 python 有输出就给中间分
        result.update({"match_type": "stdout_only_expected_broken", "score": 0.5,
                       "detail": "Python produced output, expected SQL broken"})
        return result

    # 尝试执行 expected SQL
    expected_exec = execute_sql_safe(expected_sql, allow_full_scan=True)
    if expected_exec["ok"] and expected_exec["rows"]:
        # 双方都有结果，算 F1
        actual_bag = value_bag(actual.get("rows", []))
        expected_bag = value_bag(expected_exec["rows"])

        if not actual_bag and not expected_bag:
            result.update({"match_type": "both_empty", "score": 1.0, "detail": "Both empty"})
            return result

        intersection = set(actual_bag.keys()) & set(expected_bag.keys())
        recall = len(intersection) / max(len(expected_bag), 1)
        precision = len(intersection) / max(len(actual_bag), 1)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        result.update({
            "match_type": "result_f1",
            "score": round(f1, 3),
            "detail": f"Actual rows: {len(actual.get('rows', []))}, Expected rows: {len(expected_exec['rows'])}"
        })
        return result
    else:
        # expected SQL 不可执行，只判断 actual 是否成功
        if actual.get("ok") and actual.get("rows"):
            result.update({"match_type": "actual_success_expected_broken", "score": 0.5, "detail": "Actual ran ok, expected SQL broken"})
        elif actual.get("ok") and not actual.get("rows"):
            result.update({"match_type": "actual_empty", "score": 0.3, "detail": "Actual ran ok but empty"})
        else:
            result.update({"match_type": "actual_failed", "score": 0.0, "detail": f"Actual failed: {actual.get('error', '')}"})
        return result

# ============================================================
# 评分
# ============================================================

def score_case(result: EvalResult) -> float:
    """评估单个 case，返回 0~1 总分"""
    scores = {}

    # 1. has_valid_response (20%)
    if result.actual_response and not result.actual_response.startswith("[") and len(result.actual_response) > 10:
        scores["has_valid_response"] = 1.0
    elif result.actual_response:
        scores["has_valid_response"] = 0.5
    else:
        scores["has_valid_response"] = 0.0

    # 2. code extraction (20%)
    if result.code_type in ("sql", "python"):
        scores["code_extraction"] = 1.0
    else:
        scores["code_extraction"] = 0.0

    # 3. execution success (30%)
    if result.execution_result.get("ok"):
        scores["execution_success"] = 1.0
    elif result.code_type == "none":
        scores["execution_success"] = 0.0
    else:
        scores["execution_success"] = 0.0

    # 4. result quality / correctness (30%)
    if result.execution_result.get("ok"):
        comparison = compare_results(result.execution_result, result.expected_sql)
        scores["result_quality"] = comparison["score"]
        scores["comparison_detail"] = comparison["detail"]
        scores["match_type"] = comparison["match_type"]
    else:
        scores["result_quality"] = 0.0

    # 加权总分
    weights = {
        "has_valid_response": 0.2,
        "code_extraction": 0.2,
        "execution_success": 0.3,
        "result_quality": 0.3,
    }
    total = sum(scores[k] * weights[k] for k in weights)
    result.scores = scores
    result.total_score = round(total, 3)
    return total

# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="DeerFlow 端到端评测（基于 OpenAI API，模拟 first-pass）")
    parser.add_argument("--skill", help="指定 skill 名称（如 water-situation）")
    parser.add_argument("--all-skills", action="store_true", help="跑所有 skill")
    parser.add_argument("--range", help="题号范围（如 1-10）")
    parser.add_argument("--timeout", type=int, default=120, help="单题超时（秒）")
    parser.add_argument("--dry-run", action="store_true", help="仅解析不执行")
    parser.add_argument("--output", default="reports/eval_e2e", help="输出目录")
    args = parser.parse_args()

    # 解析用例
    skills_root = Path('/opt/git/water-resources-skills/skills')
    md_path = skills_root / 'docs/test-cases-with-sql.md'
    if not md_path.exists():
        print(f"Error: {md_path} not found")
        sys.exit(1)

    all_cases = parse_test_cases(str(md_path))

    # 筛选
    if args.skill:
        cases = [c for c in all_cases if c.skill == args.skill]
    elif args.all_skills:
        cases = all_cases
    else:
        print("Error: specify --skill or --all-skills")
        sys.exit(1)

    # 范围筛选
    if args.range:
        start, end = map(int, args.range.split("-"))
        cases = [c for c in cases if start <= c.index <= end]

    print(f"\n{'='*60}")
    print(f"DeerFlow 端到端评测: {args.skill or 'ALL'}")
    print(f"用例数: {len(cases)} | Timeout: {args.timeout}s")
    print(f"{'='*60}\n")

    if args.dry_run:
        for case in cases[:10]:
            print(f"Q{case.index:03d} [{case.skill}/{case.level}]: {case.question}")
        print(f"\n... 共 {len(cases)} 题")
        return

    # 加载 DeerFlow 配置
    try:
        df_config = load_deerflow_config()
        print(f"✓ 加载 DeerFlow 配置: {df_config['model']} @ {df_config['base_url']}")
    except Exception as e:
        print(f"✗ 加载 DeerFlow 配置失败: {e}")
        sys.exit(1)

    # 加载 skill 内容
    try:
        skill_content = load_skill_content(args.skill or "water-situation", str(skills_root))
        print(f"✓ 加载 Skill: {args.skill or 'water-situation'} ({len(skill_content)} chars)\n")
    except Exception as e:
        print(f"✗ 加载 Skill 失败: {e}")
        sys.exit(1)

    # 执行
    results = []
    os.environ["WATER_RESOURCES_ROOT"] = str(skills_root)

    for i, case in enumerate(cases, 1):
        print(f"[{i:3d}/{len(cases)}] Q{case.index:03d} [{case.skill}/{case.level}]")
        print(f"  Q: {case.question[:80]}...")

        result = EvalResult(
            index=case.index,
            skill=case.skill,
            level=case.level,
            question=case.question,
            expected_sql=case.expected_sql,
        )

        # 调用 LLM
        start = time.time()
        try:
            response = call_llm(df_config, skill_content, case.question, timeout=args.timeout)
            duration = time.time() - start
            result.actual_response = response
            result.duration_sec = round(duration, 2)

            if not response or len(response) < 5:
                result.error = "[EMPTY RESPONSE]"
                result.completed = False
                score_case(result)
                results.append(result)
                print(f"  ✗ 空响应 ({duration:.1f}s)")
                continue

            print(f"  ✓ Response: {len(response)} chars ({duration:.1f}s)")

        except Exception as e:
            duration = time.time() - start
            result.error = f"[API ERROR]: {str(e)}"
            result.duration_sec = round(duration, 2)
            result.completed = False
            score_case(result)
            results.append(result)
            print(f"  ✗ API error: {str(e)[:80]}")
            continue

        # 提取代码
        code, code_type = extract_code_from_response(response)
        result.extracted_code = code
        result.code_type = code_type
        print(f"  📝 Code type: {code_type}")

        if code_type == "none":
            result.execution_result = {"ok": False, "error": "No code extracted", "rows": []}
            score_case(result)
            results.append(result)
            print(f"  ⚠️ No code extracted")
            continue

        # 执行代码
        if code_type == "sql":
            exec_result = execute_sql_safe(code, timeout=30)
            result.execution_result = exec_result
            if exec_result["ok"]:
                print(f"  ✓ SQL executed: {exec_result['row_count']} rows")
            else:
                result.execution_error = exec_result.get("error", "")
                print(f"  ✗ SQL failed: {exec_result.get('error', '')[:80]}")
        elif code_type == "python":
            exec_result = execute_python_safe(code, timeout=30)
            result.execution_result = exec_result
            if exec_result["ok"]:
                print(f"  ✓ Python ran: {len(exec_result.get('stdout', ''))} chars output")
            else:
                result.execution_error = exec_result.get("stderr", "")
                print(f"  ✗ Python failed: {exec_result.get('stderr', '')[:80]}")

        # 评分
        score = score_case(result)
        print(f"  🎯 Score: {score:.3f} | {result.scores}")
        results.append(result)

    # 生成报告
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 汇总
    total = len(results)
    avg_score = sum(r.total_score for r in results) / total if total > 0 else 0
    completed = sum(1 for r in results if r.completed and not r.error.startswith("[ERROR]") and not r.error.startswith("[TIMEOUT]"))
    timeout_count = sum(1 for r in results if "[TIMEOUT]" in r.error)

    print(f"\n{'='*60}")
    print(f"评测完成: {completed}/{total} 成功 | {timeout_count} 超时 | 平均分: {avg_score:.3f}")
    print(f"{'='*60}\n")

    # 保存 JSON
    report_data = {
        "timestamp": timestamp,
        "config": {
            "skill": args.skill or "ALL",
            "model": df_config['model'],
            "base_url": df_config['base_url'],
            "timeout": args.timeout,
            "range": args.range or "all",
            "e2e_mode": "direct_openai_api",  # 非 hermes
            "note": "Direct OpenAI API call, bypassing hermes CLI and DeerFlow Gateway. Simulates DeerFlow first-pass skill loading.",
        },
        "summary": {
            "total": total,
            "completed": completed,
            "timeout": timeout_count,
            "avg_score": round(avg_score, 3),
        },
        "results": [asdict(r) for r in results],
    }

    json_path = output_dir / f"eval_e2e_{args.skill or 'all'}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"📄 JSON 报告: {json_path}")

    # 保存 Markdown
    md_path = output_dir / f"eval_e2e_{args.skill or 'all'}_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# DeerFlow 端到端评测报告\n\n")
        f.write(f"> 模式: **直连 OpenAI API**（模拟 DeerFlow first-pass）\n")
        f.write(f"> 模型: {df_config['model']}\n")
        f.write(f"> 端点: {df_config['base_url']}\n\n")
        f.write(f"- 时间: {timestamp}\n")
        f.write(f"- Skill: {args.skill or 'ALL'}\n")
        f.write(f"- Timeout: {args.timeout}s\n")
        f.write(f"- 用例数: {total} | 完成: {completed} | 超时: {timeout_count} | 平均分: {avg_score:.3f}\n\n")

        f.write("## 结果明细\n\n")
        f.write("| Q# | Skill | Level | Score | Code Type | Status | Duration |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in results:
            status = "✓" if r.completed and r.execution_result.get("ok") else "✗"
            f.write(f"| Q{r.index:03d} | {r.skill} | {r.level} | {r.total_score:.3f} | {r.code_type} | {status} | {r.duration_sec:.1f}s |\n")

        f.write("\n## 低分 Case（< 0.5）\n\n")
        for r in sorted(results, key=lambda x: x.total_score)[:10]:
            f.write(f"### Q{r.index:03d} [{r.skill}/{r.level}] - {r.total_score:.3f}\n\n")
            f.write(f"**Q**: {r.question}\n\n")
            f.write(f"**Response** (前500字):\n```\n{r.actual_response[:500]}\n```\n\n")
            if r.extracted_code:
                f.write(f"**Extracted Code**:\n```{r.code_type}\n{r.extracted_code[:500]}\n```\n\n")
            if r.execution_error:
                f.write(f"**Error**: {r.execution_error}\n\n")
            f.write("---\n\n")

    print(f"📄 Markdown 报告: {md_path}")

    return results

if __name__ == "__main__":
    main()

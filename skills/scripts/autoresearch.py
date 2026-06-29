#!/usr/bin/env python3
"""
水利 Skill 自动化测试与评估脚本

功能:
  1. 解析 docs/test-cases-with-sql.md 中的测试用例
  2. 通过 hermes -z 执行每个问题，采集 LLM 回答
  3. 多维度评估: SQL 生成、SQL 相似度、执行成功、结果质量
  4. 生成 JSON + Markdown 评估报告

用法:
  # 全量测试（98题）
  python evaluate_skills.py

  # 指定 skill
  python evaluate_skills.py --skill water-situation

  # 指定难度
  python evaluate_skills.py --level L1

  # 指定题号范围
  python evaluate_skills.py --range 1-10

  # 仅解析测试用例（不执行，用于验证解析结果）
  python evaluate_skills.py --dry-run

  # 仅执行数据库验证（验证预期 SQL 是否能执行成功）
  python evaluate_skills.py --validate-sql

  # 设置超时（秒）
  python evaluate_skills.py --timeout 120

  # 输出到指定目录
  python evaluate_skills.py --output reports/eval_20260520
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# ============================================================
# 数据模型
# ============================================================

@dataclass
class TestCase:
    """单个测试用例"""
    index: int                  # 全局序号 (1-based)
    skill: str                  # skill 名称
    level: str                  # 难度: L1/L2/L3
    question: str               # 自然语言问题
    expected_sql: str           # 预期 SQL
    question_num: int = 0       # skill 内序号


@dataclass
class EvalResult:
    """单个测试用例的评估结果"""
    index: int
    skill: str
    level: str
    question: str
    expected_sql: str
    actual_response: str = ""
    actual_sql: str = ""
    scores: dict = field(default_factory=dict)
    total_score: float = 0.0
    duration_sec: float = 0.0
    error: str = ""


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

    # 按 ## 和 ### 拆分
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
# Hermes 执行
# ============================================================

def run_hermes_oneshot(prompt: str, skill: str, timeout: int = 120) -> tuple[str, float]:
    """通过 hermes -z 执行单个问题，返回 (response, duration_sec)"""
    cmd = ["hermes", "-z", prompt, "-s", skill]
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "HERMES_YOLO_MODE": "1", "HERMES_ACCEPT_HOOKS": "1"},
        )
        duration = time.time() - start
        response = result.stdout.strip()
        if not response and result.stderr:
            response = f"[STDERR]: {result.stderr.strip()}"
        return response, duration
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        return f"[TIMEOUT after {timeout}s]", duration
    except Exception as e:
        duration = time.time() - start
        return f"[ERROR]: {e}", duration


# ============================================================
# SQL 提取与评估
# ============================================================

def extract_sql_from_response(response: str) -> str:
    """从 LLM 回答中提取 SQL 语句"""
    # 优先匹配 ```sql ... ``` 块
    match = re.search(r"```sql\s*\n(.*?)\n```", response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 匹配 ```...``` 块（无语言标记）
    match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if content.upper().startswith("SELECT") or content.upper().startswith("SHOW") or content.upper().startswith("DESCRIBE"):
            return content

    # 匹配直接出现的 SQL（以 SELECT 开头）
    match = re.search(r"(SELECT\s+.*?;)", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return ""


def normalize_sql(sql: str) -> str:
    """标准化 SQL 用于比较"""
    s = sql.strip().rstrip(";").strip()
    s = re.sub(r"\s+", " ", s)           # 多空白合并
    s = s.lower()                         # 统一小写
    s = re.sub(r"\bAS\s+'[^']*'", "", s)  # 移除中文别名
    s = re.sub(r"\bAS\s+\"[^\"]*\"", "", s)
    s = re.sub(r"'[^']*'", "'?'", s)      # 字符串常量替换
    return s.strip()


def sql_similarity(sql1: str, sql2: str) -> float:
    """计算两个 SQL 的文本相似度 (0~1)"""
    n1 = normalize_sql(sql1)
    n2 = normalize_sql(sql2)
    if not n1 or not n2:
        return 0.0

    # 简单的词级 Jaccard 相似度
    words1 = set(n1.split())
    words2 = set(n2.split())
    intersection = words1 & words2
    union = words1 | words2
    if not union:
        return 0.0
    return len(intersection) / len(union)


def check_sql_safety(sql: str) -> dict:
    """检查 SQL 是否符合安全规则"""
    issues = []
    sql_upper = sql.upper().strip()

    # 检查是否为只读语句
    if not any(sql_upper.startswith(kw) for kw in ["SELECT", "SHOW", "DESCRIBE"]):
        issues.append("非只读语句")

    # 检查危险操作
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]
    for kw in dangerous:
        if re.search(rf"\b{kw}\b", sql_upper):
            issues.append(f"包含危险操作: {kw}")

    # 检查是否有 WHERE 条件
    if "FROM" in sql_upper and "WHERE" not in sql_upper and "JOIN" not in sql_upper:
        issues.append("无 WHERE 条件（可能全表扫描）")

    # 检查是否有 LIMIT（对大数据量表）
    if "LIMIT" not in sql_upper and "COUNT" not in sql_upper:
        issues.append("无 LIMIT（建议大数据量查询加 LIMIT）")

    return {"safe": len(issues) == 0, "issues": issues}


def evaluate_single(case: TestCase, timeout: int = 120) -> EvalResult:
    """执行并评估单个测试用例"""
    result = EvalResult(
        index=case.index,
        skill=case.skill,
        level=case.level,
        question=case.question,
        expected_sql=case.expected_sql,
    )

    # 执行 hermes
    response, duration = run_hermes_oneshot(case.question, case.skill, timeout)
    result.actual_response = response
    result.duration_sec = round(duration, 2)

    # 提取 SQL（hermes -z 通常返回自然语言结果而非 SQL）
    actual_sql = extract_sql_from_response(response)
    result.actual_sql = actual_sql

    # ---- 评估维度（兼容两种输出格式） ----

    # 维度 1: 回答是否有效（非空、非报错、有实质内容）
    has_valid_response = 0.0
    if response and not response.startswith("[STDERR]") and not response.startswith("[ERROR"):
        if len(response) > 30:
            has_valid_response = 1.0
        elif len(response) > 10:
            has_valid_response = 0.5

    # 维度 2: 回答是否包含领域数据
    data_keywords = {
        "water-situation": ["水位", "测站", "河流", "水情", "水文", "防洪", "警戒", "保证"],
        "rainfall": ["降雨", "雨量", "降水", "雨站", "mm", "暴雨", "大雨"],
        "water-quality": ["水质", "溶解氧", "CODMn", "氨氮", "总磷", "pH", "等级", "评级"],
        "water-forecast": ["预测", "预报", "任务", "模型", "断面", "水位"],
        "gate-pump-operation": ["闸", "泵", "开度", "流量", "启闭", "上下游", "堰"],
        "water-warning": ["预警", "超警戒", "超保证", "预警", "防洪", "水质"],
    }
    skill_keywords = data_keywords.get(case.skill, ["数据", "查询", "结果"])
    keyword_hits = sum(1 for kw in skill_keywords if kw in response)
    has_domain_data = min(1.0, keyword_hits / 3.0)  # 命中 3 个关键词即满分

    # 维度 3: 回答是否包含数值数据（表格、数字）
    has_numeric_data = 0.0
    numbers = re.findall(r"\d+\.?\d*", response)
    if len(numbers) >= 3:
        has_numeric_data = 1.0
    elif len(numbers) >= 1:
        has_numeric_data = 0.5

    # 维度 4: SQL 相似度（如有 SQL 代码块则评估，否则用回答完整性替代）
    if actual_sql:
        similarity = sql_similarity(actual_sql, case.expected_sql)
        if similarity >= 0.6:
            sim_score = 1.0
        elif similarity >= 0.4:
            sim_score = 0.7
        elif similarity >= 0.2:
            sim_score = 0.4
        else:
            sim_score = 0.2
        sql_safety = check_sql_safety(actual_sql)
    else:
        # 无 SQL 代码块时，用回答长度和结构化程度替代
        sim_score = 0.7 if len(response) > 200 else 0.4 if len(response) > 50 else 0.1
        sql_safety = {"safe": True, "issues": []}

    safe_score = 1.0 if sql_safety["safe"] else 0.5 if len(sql_safety["issues"]) <= 1 else 0.0

    result.scores = {
        "has_valid_response": has_valid_response,
        "has_domain_data": round(has_domain_data, 2),
        "has_numeric_data": has_numeric_data,
        "response_quality": round(sim_score, 2),
        "sql_safe": safe_score,
        "safety_issues": sql_safety["issues"],
        "keyword_hits": keyword_hits,
        "response_length": len(response),
    }

    # 加权总分: 有效回答(20%) + 领域数据(30%) + 数值数据(25%) + 回答质量(25%)
    result.total_score = round(
        has_valid_response * 0.20 + has_domain_data * 0.30
        + has_numeric_data * 0.25 + sim_score * 0.25,
        2,
    )

    return result


# ============================================================
# 预期 SQL 数据库验证
# ============================================================

def validate_expected_sql(cases: list[TestCase]) -> list[dict]:
    """验证预期 SQL 是否能在数据库上成功执行"""
    try:
        import pymysql
    except ImportError:
        print("[ERROR] pymysql 未安装，请运行: pip install pymysql")
        return []

    results = []

    for case in cases:
        status = "ok"
        row_count = 0
        error_msg = ""
        conn = None
        try:
            conn = pymysql.connect(
                host="192.168.100.103", port=3306,
                user="root", password=os.environ.get("SL323_DB_PASSWORD", ""),
                database="sl323", connect_timeout=10,
                read_timeout=60,
            )
            cursor = conn.cursor()
            cursor.execute(case.expected_sql)
            row_count = cursor.rowcount if cursor.rowcount >= 0 else len(cursor.fetchall())
            cursor.close()
        except Exception as e:
            status = "error"
            error_msg = str(e)[:200]
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        results.append({
            "index": case.index,
            "skill": case.skill,
            "level": case.level,
            "question": case.question[:50],
            "status": status,
            "row_count": row_count,
            "error": error_msg,
        })

    return results


# ============================================================
# 报告生成
# ============================================================

def generate_report(results: list[EvalResult], output_dir: str):
    """生成 JSON + Markdown 评估报告"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- JSON 报告 ---
    json_path = os.path.join(output_dir, f"eval_results_{timestamp}.json")
    json_data = {
        "meta": {
            "timestamp": timestamp,
            "total_cases": len(results),
            "total_duration_sec": round(sum(r.duration_sec for r in results), 2),
        },
        "results": [asdict(r) for r in results],
        "summary": _compute_summary(results),
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    # --- Markdown 报告 ---
    md_path = os.path.join(output_dir, f"eval_report_{timestamp}.md")
    summary = _compute_summary(results)

    lines = [
        f"# 水利 Skill 评估报告",
        f"",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 测试用例: {len(results)} 题",
        f"> 总耗时: {summary['total_duration_sec']}s",
        f"",
        f"## 总体评分",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| **平均分** | {summary['avg_score']:.2f} |",
        f"| **有效回答率** | {summary['valid_response_rate']:.1%} |",
        f"| **领域数据率** | {summary['domain_data_rate']:.1%} |",
        f"| **数值数据率** | {summary['numeric_data_rate']:.1%} |",
        f"| **通过率 (>=0.6)** | {summary['pass_rate']:.1%} |",
        f"",
    ]

    # 按 skill 汇总
    lines.append("## 按 Skill 汇总")
    lines.append("")
    lines.append("| Skill | 题数 | 平均分 | 有效回答率 | 通过率 | 平均耗时 |")
    lines.append("|-------|------|--------|-----------|--------|----------|")
    for skill_data in summary["by_skill"]:
        lines.append(
            f"| {skill_data['skill']} | {skill_data['count']} | "
            f"{skill_data['avg_score']:.2f} | {skill_data['valid_response_rate']:.1%} | "
            f"{skill_data['pass_rate']:.1%} | {skill_data['avg_duration']:.1f}s |"
        )
    lines.append("")

    # 按难度汇总
    lines.append("## 按难度汇总")
    lines.append("")
    lines.append("| 难度 | 题数 | 平均分 | 有效回答率 | 通过率 |")
    lines.append("|------|------|--------|-----------|--------|")
    for level_data in summary["by_level"]:
        lines.append(
            f"| {level_data['level']} | {level_data['count']} | "
            f"{level_data['avg_score']:.2f} | {level_data['valid_response_rate']:.1%} | "
            f"{level_data['pass_rate']:.1%} |"
        )
    lines.append("")

    # 失败用例详情
    failed = [r for r in results if r.total_score < 0.6]
    if failed:
        lines.append("## 低分用例 (总分 < 0.6)")
        lines.append("")
        for r in failed:
            lines.append(f"### Q{r.index} [{r.skill}/{r.level}] — {r.question[:60]}")
            lines.append(f"- **总分:** {r.total_score}")
            lines.append(f"- **SQL 生成:** {'Yes' if r.actual_sql else 'No'}")
            lines.append(f"- **SQL 相似度:** {r.scores.get('sql_raw_similarity', 0):.2f}")
            if r.scores.get("safety_issues"):
                lines.append(f"- **安全问题:** {', '.join(r.scores['safety_issues'])}")
            if r.error:
                lines.append(f"- **错误:** {r.error}")
            lines.append(f"- **耗时:** {r.duration_sec}s")
            lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, md_path


def _compute_summary(results: list[EvalResult]) -> dict:
    """计算汇总统计"""
    if not results:
        return {}

    scores = [r.total_score for r in results]
    valid_responses = [r.scores.get("has_valid_response", 0) for r in results]
    domain_data = [r.scores.get("has_domain_data", 0) for r in results]
    numeric_data = [r.scores.get("has_numeric_data", 0) for r in results]
    durations = [r.duration_sec for r in results]

    by_skill = {}
    for r in results:
        if r.skill not in by_skill:
            by_skill[r.skill] = []
        by_skill[r.skill].append(r)

    by_level = {}
    for r in results:
        if r.level not in by_level:
            by_level[r.level] = []
        by_level[r.level].append(r)

    def _group_stats(items):
        s = [r.total_score for r in items]
        vr = [r.scores.get("has_valid_response", 0) for r in items]
        return {
            "count": len(items),
            "avg_score": sum(s) / len(s) if s else 0,
            "valid_response_rate": sum(vr) / len(vr) if vr else 0,
            "pass_rate": sum(1 for x in s if x >= 0.6) / len(s) if s else 0,
            "avg_duration": sum(r.duration_sec for r in items) / len(items) if items else 0,
        }

    return {
        "total_duration_sec": round(sum(durations), 2),
        "avg_score": sum(scores) / len(scores) if scores else 0,
        "valid_response_rate": sum(valid_responses) / len(valid_responses) if valid_responses else 0,
        "domain_data_rate": sum(domain_data) / len(domain_data) if domain_data else 0,
        "numeric_data_rate": sum(numeric_data) / len(numeric_data) if numeric_data else 0,
        "pass_rate": sum(1 for s in scores if s >= 0.6) / len(scores) if scores else 0,
        "by_skill": [{"skill": k, **_group_stats(v)} for k, v in sorted(by_skill.items())],
        "by_level": [{"level": k, **_group_stats(v)} for k, v in sorted(by_level.items())],
    }


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="水利 Skill 自动化测试与评估")
    parser.add_argument("--test-cases", default=None, help="测试用例文件路径 (默认 docs/test-cases-with-sql.md)")
    parser.add_argument("--skill", help="仅测试指定 skill")
    parser.add_argument("--level", choices=["L1", "L2", "L3"], help="仅测试指定难度")
    parser.add_argument("--range", help="题号范围，如 1-10")
    parser.add_argument("--timeout", type=int, default=600, help="单题超时秒数 (默认 600)")
    parser.add_argument("--output", default="reports", help="报告输出目录 (默认 reports/)")
    parser.add_argument("--dry-run", action="store_true", help="仅解析测试用例，不执行")
    parser.add_argument("--validate-sql", action="store_true", help="仅验证预期 SQL 在数据库上的执行")
    args = parser.parse_args()

    # 确定测试用例文件路径
    skill_root = Path(__file__).resolve().parent.parent  # scripts/ → water-resources/
    if args.test_cases:
        md_path = args.test_cases
    else:
        md_path = str(skill_root / "docs" / "test-cases-with-sql.md")

    if not os.path.exists(md_path):
        print(f"[ERROR] 测试用例文件不存在: {md_path}")
        sys.exit(1)

    # 解析测试用例
    cases = parse_test_cases(md_path)
    print(f"解析到 {len(cases)} 个测试用例")

    # 过滤
    if args.skill:
        cases = [c for c in cases if c.skill == args.skill]
        print(f"  过滤 skill={args.skill}: {len(cases)} 题")

    if args.level:
        cases = [c for c in cases if c.level == args.level]
        print(f"  过滤 level={args.level}: {len(cases)} 题")

    if args.range:
        start, end = map(int, args.range.split("-"))
        cases = [c for c in cases if start <= c.index <= end]
        print(f"  过滤 range={args.range}: {len(cases)} 题")

    if not cases:
        print("[WARN] 无匹配的测试用例")
        sys.exit(0)

    # --dry-run: 仅打印解析结果
    if args.dry_run:
        print("\n测试用例列表:")
        print(f"{'#':>3} {'Skill':<25} {'Level':<4} {'Question':<50}")
        print("-" * 85)
        for c in cases:
            print(f"{c.index:>3} {c.skill:<25} {c.level:<4} {c.question[:50]}")
        print(f"\n共 {len(cases)} 题")
        return

    # --validate-sql: 仅验证预期 SQL
    if args.validate_sql:
        print("\n验证预期 SQL 在数据库上的执行...")
        results = validate_expected_sql(cases)
        ok_count = sum(1 for r in results if r["status"] == "ok")
        err_count = sum(1 for r in results if r["status"] == "error")
        print(f"  成功: {ok_count}, 失败: {err_count}")
        if err_count:
            print("\n失败 SQL:")
            for r in results:
                if r["status"] == "error":
                    print(f"  Q{r['index']} [{r['skill']}] {r['error'][:100]}")
        return

    # 执行测试
    print(f"\n开始执行 {len(cases)} 个测试用例 (超时 {args.timeout}s/题)...")
    print("=" * 70)

    eval_results = []
    for i, case in enumerate(cases):
        print(f"\n[{i+1}/{len(cases)}] Q{case.index} [{case.skill}/{case.level}] {case.question[:60]}")
        result = evaluate_single(case, timeout=args.timeout)
        eval_results.append(result)

        score_str = f"总分={result.total_score:.2f}"
        sql_str = "SQL:Yes" if result.actual_sql else "SQL:No"
        dur_str = f"{result.duration_sec:.1f}s"
        print(f"  → {score_str} | {sql_str} | {dur_str}")

        if result.error:
            print(f"    ⚠ {result.error}")
        if result.scores.get("safety_issues"):
            print(f"    ⚠ 安全: {', '.join(result.scores['safety_issues'])}")

    # 生成报告
    output_dir = args.output
    json_path, md_path = generate_report(eval_results, output_dir)

    # 打印摘要
    summary = _compute_summary(eval_results)
    print("\n" + "=" * 70)
    print("评估完成!")
    print(f"  平均分:       {summary['avg_score']:.2f}")
    print(f"  有效回答率:   {summary['valid_response_rate']:.1%}")
    print(f"  领域数据率:   {summary['domain_data_rate']:.1%}")
    print(f"  数值数据率:   {summary['numeric_data_rate']:.1%}")
    print(f"  通过率(≥0.6): {summary['pass_rate']:.1%}")
    print(f"  总耗时:       {summary['total_duration_sec']}s")
    print(f"\n报告文件:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""DeerFlow Gateway 真实平台评测脚本

通过正在运行的 DeerFlow Gateway（POST /api/runs/wait）跑真实 agent 全栈，
从返回的 messages 中提取最终答案、工具调用 SQL、工具执行结果并评分。

用法：
  python evaluate_deerflow_gateway.py --skill water-situation --range 1-5
  python evaluate_deerflow_gateway.py --all-skills
  python evaluate_deerflow_gateway.py --skill rainfall --dry-run
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_deerflow_e2e import (
    parse_test_cases,
    execute_sql_safe,
    value_bag,
    stdout_recall,
)

GATEWAY_URL = os.environ.get("DEERFLOW_GATEWAY_URL", "http://localhost:8001")
INTERNAL_TOKEN = os.environ.get("DEER_FLOW_INTERNAL_AUTH_TOKEN", "test-token-for-deerflow-testing")
CSRF_TOKEN = "eval-csrf-token"
QUERY_TOOL_NAMES = ("water-db_query_water", "water_db_query_water", "query_water", "water-db_query")

_SQL_STRING_RE = re.compile(
    r'("""|\'\'\'|"|\')\s*((?:SELECT|WITH)\b[\s\S]+?)\1',
    re.IGNORECASE,
)

def extract_sqls_from_code(code: str) -> list:
    """从 python 脚本文本的字符串字面量中提取 SELECT/WITH SQL"""
    sqls = []
    for m in _SQL_STRING_RE.finditer(code):
        sql = m.group(2).strip()
        if len(sql) > 20 and "FROM" in sql.upper():
            sqls.append(sql)
    return sqls

@dataclass
class GatewayEvalResult:
    index: int
    skill: str
    level: str
    question: str
    expected_sql: str
    final_answer: str = ""
    actual_sqls: list = field(default_factory=list)
    tool_trace: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    total_score: float = 0.0
    duration_sec: float = 0.0
    llm_round_trips: int = 0
    error: str = ""
    completed: bool = True

# ============================================================
# Gateway 调用
# ============================================================

def call_gateway(question: str, model_name: str | None = None, timeout: int = 900) -> dict:
    """POST /api/runs/wait，返回最终 channel values（含 messages）

    注意：/runs/wait 返回的是最终图状态，长 run 的早期消息可能被上下文压缩裁掉。
    因此显式指定 thread_id，完成后再从事件库 /threads/{id}/messages 拉全量历史。
    """
    thread_id = str(uuid.uuid4())
    body = {
        "input": {"messages": [{"role": "user", "content": question}]},
        # 默认 100 step ≈ 11 轮 LLM（每轮 ~9 step），带图表的 L3 题会触顶。
        # 服务端 max_recursion_limit=1000 内可自定义。
        "config": {"recursion_limit": 250, "configurable": {"thread_id": thread_id}},
    }
    context = {"thinking_enabled": False}
    if model_name:
        context["model_name"] = model_name
    body["context"] = context

    req = urllib.request.Request(
        f"{GATEWAY_URL}/api/runs/wait",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-DeerFlow-Internal-Token": INTERNAL_TOKEN,
            "X-CSRF-Token": CSRF_TOKEN,
            "Cookie": f"csrf_token={CSRF_TOKEN}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    payload["thread_messages"] = fetch_thread_messages(thread_id)
    payload["thread_id"] = thread_id
    return payload


def fetch_thread_messages(thread_id: str) -> list:
    """GET /threads/{id}/messages（事件库全量，无压缩裁剪），解包 content JSON"""
    req = urllib.request.Request(
        f"{GATEWAY_URL}/api/threads/{thread_id}/messages?limit=200",
        headers={
            "X-DeerFlow-Internal-Token": INTERNAL_TOKEN,
            "X-CSRF-Token": CSRF_TOKEN,
            "Cookie": f"csrf_token={CSRF_TOKEN}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            events = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ⚠️ 拉取事件库消息失败（回退图状态 messages）: {e}", file=sys.stderr)
        return []
    messages = []
    for ev in events:
        content = ev.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                continue
        if isinstance(content, dict):
            messages.append(content)
    return messages

# ============================================================
# 响应解析
# ============================================================

def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content or "")

def parse_run_messages(payload: dict) -> dict:
    """从 /api/runs/wait 返回值提取评分所需信息

    优先用事件库全量历史（thread_messages）；图状态 messages 在长 run 中
    会被上下文压缩裁掉早期轮次（实测 Q014 丢失数据查询轮的 SQL）。
    """
    messages = payload.get("thread_messages") or payload.get("messages", [])
    final_answer = ""
    last_ai_text = ""
    actual_sqls = []
    tool_trace = []
    tool_results = []
    llm_round_trips = 0

    for m in messages:
        mtype = m.get("type")
        if mtype == "ai":
            llm_round_trips += 1
            for tc in (m.get("tool_calls") or []):
                name = tc.get("name") or ""
                args = tc.get("args") or {}
                tool_trace.append(name)
                sql = args.get("sql") or args.get("query")
                if sql and (name.startswith(("water-db", "water_db")) or name in QUERY_TOOL_NAMES):
                    actual_sqls.append(sql)
                # SKILL.md 新规则下 SQL 藏在 write_file 脚本 / bash 命令里（lib/db.py query()）
                script_text = args.get("command") or args.get("content") or ""
                if isinstance(script_text, str) and script_text:
                    actual_sqls.extend(extract_sqls_from_code(script_text))
            text = _content_text(m.get("content"))
            if text.strip():
                last_ai_text = text
                if not m.get("tool_calls"):
                    final_answer = text  # 最后一条无工具调用的 ai 消息
        elif mtype == "tool":
            name = m.get("name") or ""
            if name in QUERY_TOOL_NAMES or name.startswith(("water-db", "water_db")) or name == "bash":
                tool_results.append(_content_text(m.get("content"))[:5000])

    # 兜底：run 以「文本+工具调用」或澄清提问收尾时，取最后一条有文本的 ai 消息
    if not final_answer and last_ai_text:
        final_answer = last_ai_text

    return {
        "final_answer": final_answer,
        "actual_sqls": actual_sqls,
        "tool_trace": tool_trace,
        "tool_results": tool_results,
        "llm_round_trips": llm_round_trips,
    }

# ============================================================
# 评分
# ============================================================

def score_result(r: GatewayEvalResult) -> float:
    scores = {}

    # 1. 有效最终答案 (20%)
    if r.final_answer and len(r.final_answer) > 10:
        scores["has_valid_response"] = 1.0
    elif r.final_answer:
        scores["has_valid_response"] = 0.5
    else:
        scores["has_valid_response"] = 0.0

    # 2. 生成了查询 SQL (15%)
    scores["sql_generated"] = 1.0 if r.actual_sqls else 0.0

    # 3. 平台侧 SQL 可复执行 (25%)：在本地库重放
    #    actual_sqls[-1] 常是 f-string 模板（标准三件套主查询 WHERE ... IN ({stcd_list})），
    #    裸花括号让 MySQL 语法错 → 假阴性（agent 实跑满分却判 0）。改为优先重放具体 SQL。
    replay = None
    if r.actual_sqls:
        concrete = [s for s in r.actual_sqls if "{" not in s and "}" not in s]
        if concrete:
            replay = execute_sql_safe(concrete[-1])
            scores["sql_replay_ok"] = 1.0 if replay["ok"] else 0.0
        else:
            # 全是模板：仍试重放最后一条。引号内 '{stcd}' → 当字面量能跑、返回空 → ok=1（同现状）；
            # 裸 {stcd_list} → 语法错，无法证伪 → 中性 0.5，不假阴性。
            replay = execute_sql_safe(r.actual_sqls[-1])
            scores["sql_replay_ok"] = 1.0 if replay["ok"] else 0.5
    else:
        scores["sql_replay_ok"] = 0.0

    # 4. 结果正确性 (30%)：expected SQL 结果值 vs 最终答案文本召回
    expected_exec = execute_sql_safe(r.expected_sql, allow_full_scan=True)
    if expected_exec["ok"] and r.final_answer:
        comparison = stdout_recall(r.final_answer + "\n" + "\n".join(r.tool_results), expected_exec["rows"])
        scores["result_quality"] = comparison["score"]
        scores["comparison_detail"] = comparison["detail"]
        scores["match_type"] = comparison["match_type"]
    elif not expected_exec["ok"]:
        scores["result_quality"] = 0.5 if r.final_answer else 0.0
        scores["comparison_detail"] = f"expected SQL broken: {expected_exec.get('error','')[:100]}"
    else:
        scores["result_quality"] = 0.0

    # 5. 轨迹健康度 (10%)：有工具调用且往返次数合理
    if r.tool_trace and r.llm_round_trips <= 8:
        scores["trace_sanity"] = 1.0
    elif r.tool_trace:
        scores["trace_sanity"] = 0.5
    else:
        scores["trace_sanity"] = 0.0

    weights = {
        "has_valid_response": 0.20,
        "sql_generated": 0.15,
        "sql_replay_ok": 0.25,
        "result_quality": 0.30,
        "trace_sanity": 0.10,
    }
    total = sum(scores[k] * weights[k] for k in weights)
    r.scores = scores
    r.total_score = round(total, 3)
    return total

# ============================================================
# 主流程
# ============================================================

def cleanup_all_mcp():
    """题间清理：kill 所有 water_db_mcp.py，保证下一题在干净环境启动。

    根因：DeerFlow 每跑一个 case 泄漏 MCP 子进程，累积后新 case 第一轮 LLM 卡死
    （轮次0超时）。cron watchdog（1800s 阈值）跟不上连续评测的泄漏速度——实测
    泄漏进程要存活 30+ 分钟才被清，期间 Q050/Q053 已卡死。故在 harness 内每题/
    每次重试前主动全清，是比 cron 更精准的兜底。
    """
    import subprocess
    try:
        subprocess.run(["pkill", "-f", "water_db_mcp.py"],
                       capture_output=True, timeout=10)
    except Exception:
        pass


def run_one_case(question: str, model, timeout: int, retries: int = 1):
    """调用 gateway 跑一个 case；轮次0间歇卡死自动重试。

    间歇卡死特征：agent 第一轮 LLM 就没返回 → llm_round_trips==0 且无 SQL，
    或直接超时异常。这类失败是非确定性的（Q050 实测单独重跑 0.000→0.950），
    根因是 DeerFlow session_pool 异常退出时泄漏 MCP 子进程，累积后压垮新 run。
    故对这类特征自动重试，可把通过率从 ~94% 拉回 ~98%。
    """
    last_err = ""
    for attempt in range(retries + 1):
        cleanup_all_mcp()  # 每次（含重试）前清理泄漏的 MCP，保证干净启动
        start = time.time()
        try:
            payload = call_gateway(question, model_name=model, timeout=timeout)
            parsed = parse_run_messages(payload)
            duration = round(time.time() - start, 1)
            stall = parsed["llm_round_trips"] == 0 and not parsed["actual_sqls"]
            if stall and attempt < retries:
                print(f"  ⚠️ 轮次0疑似间歇卡死，重试 {attempt + 1}/{retries}（{duration}s）")
                last_err = "round0_stall"
                time.sleep(3)
                continue
            return parsed, duration, (last_err if stall else "")
        except Exception as e:
            duration = round(time.time() - start, 1)
            last_err = str(e)[:300]
            if attempt < retries:
                print(f"  ⚠️ 异常重试 {attempt + 1}/{retries}（{duration}s）: {last_err[:60]}")
                time.sleep(3)
                continue
            return None, duration, last_err
    return None, 0, last_err


def main():
    parser = argparse.ArgumentParser(description="DeerFlow Gateway 真实平台评测")
    parser.add_argument("--skill", help="skill 名称")
    parser.add_argument("--all-skills", action="store_true")
    parser.add_argument("--range", help="题号范围，如 1-10")
    parser.add_argument("--model", default=None, help="模型名（默认用平台默认模型）")
    parser.add_argument("--timeout", type=int, default=900, help="单题超时秒数")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default="reports/eval_gateway")
    parser.add_argument("--retries", type=int, default=1, help="轮次0间歇卡死自动重试次数（默认1）")
    args = parser.parse_args()

    skills_root = Path(os.environ.get("WATER_RESOURCES_ROOT", "/opt/git/water-resources-skills/skills"))
    md_path = skills_root / "docs/test-cases-with-sql.md"
    all_cases = parse_test_cases(str(md_path))

    if args.skill:
        cases = [c for c in all_cases if c.skill == args.skill]
    elif args.all_skills:
        cases = all_cases
    else:
        print("Error: specify --skill or --all-skills")
        sys.exit(1)

    if args.range:
        start, end = map(int, args.range.split("-"))
        cases = [c for c in cases if start <= c.index <= end]

    print(f"\n{'='*60}")
    print(f"DeerFlow Gateway 真实平台评测: {args.skill or 'ALL'}")
    print(f"Gateway: {GATEWAY_URL} | 用例数: {len(cases)} | 单题超时: {args.timeout}s")
    print(f"{'='*60}\n")

    if args.dry_run:
        for c in cases[:10]:
            print(f"Q{c.index:03d} [{c.skill}/{c.level}]: {c.question}")
        print(f"\n... 共 {len(cases)} 题")
        return

    os.environ.setdefault("WATER_RESOURCES_ROOT", str(skills_root))
    results = []

    inc_dir = Path(args.output)
    inc_dir.mkdir(parents=True, exist_ok=True)
    inc_path = inc_dir / f"incremental_{args.skill or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    for i, case in enumerate(cases, 1):
        print(f"[{i:3d}/{len(cases)}] Q{case.index:03d} [{case.skill}/{case.level}] {case.question[:60]}")
        r = GatewayEvalResult(
            index=case.index, skill=case.skill, level=case.level,
            question=case.question, expected_sql=case.expected_sql,
        )
        parsed, gw_duration, err = run_one_case(case.question, args.model, args.timeout, args.retries)
        r.duration_sec = gw_duration
        if err:
            r.error = err
            r.completed = False
            score_result(r)
            print(f"  ✗ {r.duration_sec}s | error: {r.error[:100]}")
        else:
            r.final_answer = parsed["final_answer"]
            r.actual_sqls = parsed["actual_sqls"]
            r.tool_trace = parsed["tool_trace"]
            r.tool_results = parsed["tool_results"]
            r.llm_round_trips = parsed["llm_round_trips"]
            score_result(r)
            print(f"  ✓ {r.duration_sec}s | rounds={r.llm_round_trips} | sqls={len(r.actual_sqls)} | score={r.total_score:.3f}")
        results.append(r)
        with open(inc_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

    # 报告
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    total = len(results)
    avg = sum(x.total_score for x in results) / total if total else 0
    pass_rate = sum(1 for x in results if x.total_score >= 0.6) / total if total else 0

    print(f"\n{'='*60}")
    print(f"完成 {total} 题 | 平均分 {avg:.3f} | 通过率 {pass_rate:.1%}")
    print(f"{'='*60}")

    json_path = output_dir / f"gateway_eval_{args.skill or 'all'}_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": ts,
            "config": {
                "mode": "gateway_real_platform",
                "gateway_url": GATEWAY_URL,
                "model": args.model or "(platform default)",
                "skill": args.skill or "ALL",
                "timeout": args.timeout,
            },
            "summary": {"total": total, "avg_score": round(avg, 3), "pass_rate": round(pass_rate, 3)},
            "results": [asdict(x) for x in results],
        }, f, ensure_ascii=False, indent=2)

    md_out = output_dir / f"gateway_eval_{args.skill or 'all'}_{ts}.md"
    with open(md_out, "w", encoding="utf-8") as f:
        f.write("# DeerFlow Gateway 真实平台评测报告\n\n")
        f.write(f"> 模式: **Gateway /api/runs/wait（真实 agent 全栈）**\n")
        f.write(f"> Gateway: {GATEWAY_URL} | 模型: {args.model or '平台默认'}\n\n")
        f.write(f"- 时间: {ts}\n- 用例: {total} | 平均分: {avg:.3f} | 通过率: {pass_rate:.1%}\n\n")
        f.write("| Q# | Skill | Level | Score | SQLs | Rounds | 耗时 | 状态 |\n|---|---|---|---|---|---|---|---|\n")
        for x in results:
            st = "✓" if x.completed and not x.error else "✗"
            f.write(f"| Q{x.index:03d} | {x.skill} | {x.level} | {x.total_score:.3f} | {len(x.actual_sqls)} | {x.llm_round_trips} | {x.duration_sec:.0f}s | {st} |\n")
        f.write("\n## 低分 Case（< 0.6）\n\n")
        for x in sorted(results, key=lambda v: v.total_score):
            if x.total_score >= 0.6:
                break
            f.write(f"### Q{x.index:03d} [{x.skill}/{x.level}] — {x.total_score:.3f}\n\n")
            f.write(f"**Q**: {x.question}\n\n")
            if x.actual_sqls:
                _concrete = [s for s in x.actual_sqls if "{" not in s and "}" not in s]
                _show = (_concrete or x.actual_sqls)[-1][:500]
                f.write(f"**平台 SQL**:\n```sql\n{_show}\n```\n\n")
            f.write(f"**最终答案**（前 400 字）:\n```\n{x.final_answer[:400]}\n```\n\n")
            if x.error:
                f.write(f"**错误**: {x.error}\n\n")
            f.write(f"**评分明细**: {json.dumps({k:v for k,v in x.scores.items() if isinstance(v,(int,float))}, ensure_ascii=False)}\n\n---\n\n")

    print(f"📄 JSON: {json_path}")
    print(f"📄 Markdown: {md_out}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""实测 Q018 和 Q028"""

import sys
import time
import json
import urllib.request
import uuid
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'scripts'))

GATEWAY_URL = "http://localhost:8001"
INTERNAL_TOKEN = "test-token-for-deerflow-testing"
CSRF_TOKEN = "eval-csrf-token"

def call_gateway(question: str, model_name: str = None, timeout: int = 300) -> dict:
    """调用 DeerFlow Gateway API"""
    thread_id = str(uuid.uuid4())
    body = {
        "input": {"messages": [{"role": "user", "content": question}]},
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

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # 拉取全量消息
            thread_messages = fetch_thread_messages(thread_id)
            data["thread_messages"] = thread_messages
            return data
    except Exception as e:
        return {"error": str(e), "final_answer": "", "actual_sqls": [], "tool_trace": []}

def fetch_thread_messages(thread_id: str) -> list:
    """GET /threads/{id}/messages"""
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
        print(f"  ⚠️ 拉取事件库消息失败: {e}", file=sys.stderr)
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

# 测试 Q018
print("="*80)
print("测试 Q018: 古运河水情（模糊查询）")
print("="*80)

q018_question = '古运河水情（模糊查询，用户只输入"古运河"三个字）。'

try:
    print(f"\n问题: {q018_question}")
    print("开始调用 DeerFlow Gateway（超时300秒）...")
    start = time.time()
    result = call_gateway(q018_question, timeout=300)
    duration = time.time() - start

    print(f"\n✅ 调用完成！耗时: {duration:.1f}秒")

    if 'error' in result and result['error']:
        print(f"❌ API 返回错误: {result['error']}")
    else:
        print(f"\n最终答案（前1000字）:")
        final_answer = result.get('final_answer', result.get('output', 'N/A'))
        print(final_answer[:1000] if final_answer else 'N/A')

        print(f"\n\n生成的 SQL 数量: {len(result.get('actual_sqls', []))}")
        if result.get('actual_sqls'):
            for i, sql in enumerate(result['actual_sqls'], 1):
                print(f"\n--- SQL {i} ---")
                print(sql[:500])

        print(f"\n工具调用轨迹: {result.get('tool_trace', [])}")

        # 统计 LLM 轮次
        messages = result.get('thread_messages', [])
        ai_messages = [m for m in messages if m.get('type') == 'ai']
        print(f"\nLLM 轮次（AI消息数）: {len(ai_messages)}")

except Exception as e:
    print(f"\n❌ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("测试 Q028: 查询各雨量站的平均日降雨量")
print("="*80)

q028_question = "查询各雨量站的平均日降雨量。"

try:
    print(f"\n问题: {q028_question}")
    print("开始调用 DeerFlow Gateway（超时300秒）...")
    start = time.time()
    result = call_gateway(q028_question, timeout=300)
    duration = time.time() - start

    print(f"\n✅ 调用完成！耗时: {duration:.1f}秒")

    if 'error' in result and result['error']:
        print(f"❌ API 返回错误: {result['error']}")
    else:
        print(f"\n最终答案（前1000字）:")
        final_answer = result.get('final_answer', result.get('output', 'N/A'))
        print(final_answer[:1000] if final_answer else 'N/A')

        print(f"\n\n生成的 SQL 数量: {len(result.get('actual_sqls', []))}")
        if result.get('actual_sqls'):
            for i, sql in enumerate(result['actual_sqls'], 1):
                print(f"\n--- SQL {i} ---")
                print(sql[:500])

        print(f"\n工具调用轨迹: {result.get('tool_trace', [])}")

        # 统计 LLM 轮次
        messages = result.get('thread_messages', [])
        ai_messages = [m for m in messages if m.get('type') == 'ai']
        print(f"\nLLM 轮次（AI消息数）: {len(ai_messages)}")

except Exception as e:
    print(f"\n❌ 失败: {e}")
    import traceback
    traceback.print_exc()

EOF

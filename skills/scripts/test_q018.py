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
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data
    except Exception as e:
        return {"error": str(e), "final_answer": "", "actual_sqls": [], "tool_trace": []}

# 测试 Q018
print("="*80)
print("测试 Q018: 古运河水情（模糊查询）")
print("="*80)

q018_question = '古运河水情（模糊查询，用户只输入"古运河"三个字）。'

try:
    print(f"\n问题: {q018_question}")
    print("开始调用 DeerFlow Gateway...")
    start = time.time()
    result = call_gateway(q018_question, timeout=300)
    duration = time.time() - start

    print(f"\n✅ 调用完成！耗时: {duration:.1f}秒")
    print(f"状态: {result.keys()}")

    if 'error' in result and result['error']:
        print(f"\n❌ API 返回错误: {result['error']}")
    else:
        print(f"\n最终答案（前500字）:")
        final_answer = result.get('final_answer', result.get('output', 'N/A'))
        print(final_answer[:500] if final_answer else 'N/A')

        print(f"\n生成的 SQL 数量: {len(result.get('actual_sqls', []))}")
        if result.get('actual_sqls'):
            for i, sql in enumerate(result['actual_sqls'][:3], 1):
                print(f"\nSQL {i}:")
                print(sql[:300])

        print(f"\n工具调用: {result.get('tool_trace', [])[:10]}")

except Exception as e:
    print(f"\n❌ 失败: {e}")
    import traceback
    traceback.print_exc()

EOF

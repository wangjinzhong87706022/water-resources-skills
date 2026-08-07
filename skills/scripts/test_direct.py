#!/usr/bin/env python3
"""直接测试 Q018 和 Q028"""

import sys
import time
import json
import traceback
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'scripts'))

print("="*80)
print("直接测试 Q018 和 Q028")
print("="*80)

# 方法1: 手动构建请求并调用 DeerFlow Gateway
try:
    import urllib.request
    import uuid

    GATEWAY_URL = "http://localhost:8001"

    # 从环境变量或配置文件中读取 token
    # 先尝试从 DeerFlow 的 .env 文件读取
    deerflow_env = Path("/opt/git/deer-flow/backend/.env")
    INTERNAL_TOKEN = "test-token-for-deerflow-testing"
    CSRF_TOKEN = "eval-csrf-token"

    if deerflow_env.exists():
        print(f"\n找到 DeerFlow .env 文件: {deerflow_env}")
        with open(deerflow_env) as f:
            for line in f:
                if "DEER_FLOW_INTERNAL_AUTH_TOKEN" in line or "INTERNAL_AUTH_TOKEN" in line:
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if token:
                        INTERNAL_TOKEN = token
                        print(f"从 .env 读取到 INTERNAL_TOKEN")
                        break

    print(f"\n使用 INTERNAL_TOKEN: {INTERNAL_TOKEN[:20]}...")

    # 测试 Q018
    print("\n" + "="*80)
    print("Q018: 古运河水情（模糊查询）")
    print("="*80)

    question = '古运河水情（模糊查询，用户只输入"古运河"三个字）。'

    thread_id = str(uuid.uuid4())
    body = {
        "input": {"messages": [{"role": "user", "content": question}]},
        "config": {"recursion_limit": 50, "configurable": {"thread_id": thread_id}},
    }
    context = {"thinking_enabled": False}
    body["context"] = context

    print(f"\n发送请求到 {GATEWAY_URL}/api/runs/wait")
    print(f"Thread ID: {thread_id}")

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

    print(f"等待响应（超时120秒）...")
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"✅ 收到响应！状态码: {resp.status}")
            data = json.loads(resp.read().decode("utf-8"))
            duration = time.time() - start

            print(f"耗时: {duration:.1f}秒")
            print(f"响应 keys: {list(data.keys())}")

            # 检查是否有 messages
            messages = data.get("messages", [])
            print(f"messages 数量: {len(messages)}")

            if messages:
                print(f"\n前3条消息:")
                for i, msg in enumerate(messages[:3], 1):
                    print(f"\n{i}. {msg.get('type', 'unknown')}:")
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        print(content[:300])
                    elif isinstance(content, list):
                        for block in content[:2]:
                            if isinstance(block, dict):
                                print(f"  - {block.get('type', '?')}: {str(block.get('text', ''))[:200]}")
                    else:
                        print(str(content)[:300])

            # 拉取线程消息
            print(f"\n尝试拉取线程消息...")
            thread_req = urllib.request.Request(
                f"{GATEWAY_URL}/api/threads/{thread_id}/messages?limit=50",
                headers={
                    "X-DeerFlow-Internal-Token": INTERNAL_TOKEN,
                    "X-CSRF-Token": CSRF_TOKEN,
                    "Cookie": f"csrf_token={CSRF_TOKEN}",
                },
            )
            try:
                with urllib.request.urlopen(thread_req, timeout=30) as thread_resp:
                    thread_data = json.loads(thread_resp.read().decode("utf-8"))
                    print(f"✅ 线程消息数量: {len(thread_data)}")

                    # 统计 LLM 轮次
                    ai_msgs = [m for m in thread_data if isinstance(m, dict) and m.get("type") == "ai"]
                    tool_msgs = [m for m in thread_data if isinstance(m, dict) and m.get("type") == "tool"]

                    print(f"AI 消息数: {len(ai_msgs)}")
                    print(f"Tool 消息数: {len(tool_msgs)}")

            except Exception as e:
                print(f"❌ 拉取线程消息失败: {e}")

    except urllib.error.HTTPError as e:
        duration = time.time() - start
        print(f"❌ HTTP 错误！状态码: {e.code}")
        print(f"耗时: {duration:.1f}秒")
        print(f"错误信息: {e.read().decode('utf-8')[:500]}")

    except Exception as e:
        duration = time.time() - start
        print(f"❌ 异常！耗时: {duration:.1f}秒")
        print(f"错误: {e}")
        traceback.print_exc()

except Exception as e:
    print(f"\n❌ 失败: {e}")
    traceback.print_exc()

print("\n" + "="*80)
print("完成")
print("="*80)

EOF

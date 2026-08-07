#!/usr/bin/env python3
"""直接测试 Q018 和 Q028 - 增强版"""

import sys
import time
import json
import traceback
import urllib.request
import uuid
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'scripts'))

print("="*80)
print("直接测试 Q018 和 Q028 - 增强版")
print("="*80)

GATEWAY_URL = "http://localhost:8001"
CSRF_TOKEN = "eval-csrf-token"

# 从 DeerFlow 的 .env 文件读取 token
INTERNAL_TOKEN = "test-token-for-deerflow-testing"
deerflow_env = Path("/opt/git/deer-flow/backend/.env")

if deerflow_env.exists():
    print(f"\n✅ 找到 DeerFlow .env 文件")
    with open(deerflow_env) as f:
        for line in f:
            if "DEER_FLOW_INTERNAL_AUTH_TOKEN" in line or "INTERNAL_AUTH_TOKEN" in line:
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                if token:
                    INTERNAL_TOKEN = token
                    print(f"✅ 从 .env 读取到 INTERNAL_TOKEN")
                    break

print(f"Token: {INTERNAL_TOKEN[:30]}...")

def test_question(q_num, skill, question, timeout=120):
    """测试单个问题"""
    print("\n" + "="*80)
    print(f"Q{q_num:03d}: {question}")
    print("="*80)

    thread_id = str(uuid.uuid4())
    body = {
        "input": {"messages": [{"role": "user", "content": question}]},
        "config": {"recursion_limit": 30, "configurable": {"thread_id": thread_id}},
    }
    context = {"thinking_enabled": False}
    body["context"] = context

    print(f"\n发送请求...")
    print(f"Thread ID: {thread_id}")
    print(f"超时设置: {timeout}秒")

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

    start = time.time()
    result = {
        "question": question,
        "thread_id": thread_id,
        "duration": 0,
        "success": False,
        "error": None,
        "status_code": None,
        "response": None,
        "thread_messages": [],
    }

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["status_code"] = resp.status
            result["success"] = True
            data = json.loads(resp.read().decode("utf-8"))
            result["response"] = data
            result["duration"] = time.time() - start

            print(f"\n✅ 收到响应！状态码: {resp.status}")
            print(f"耗时: {result['duration']:.1f}秒")

            # 检查响应结构
            print(f"响应 keys: {list(data.keys())}")

            # 检查 messages
            messages = data.get("messages", [])
            print(f"messages 数量: {len(messages)}")

            if messages:
                print(f"\n前2条消息:")
                for i, msg in enumerate(messages[:2], 1):
                    msg_type = msg.get("type", "unknown")
                    print(f"\n{i}. 类型: {msg_type}")

                    content = msg.get("content", "")
                    if isinstance(content, str):
                        print(f"内容（前300字符）: {content[:300]}")
                    elif isinstance(content, list):
                        for block in content[:2]:
                            if isinstance(block, dict):
                                block_type = block.get("type", "?")
                                if block_type == "text":
                                    print(f"  - {block_type}: {block.get('text', '')[:200]}")
                                elif block_type == "tool_use":
                                    print(f"  - {block_type}: {block.get('name', '?')}")
                    else:
                        print(f"内容: {str(content)[:300]}")

            # 尝试拉取线程消息
            print(f"\n尝试拉取线程消息...")
            try:
                thread_req = urllib.request.Request(
                    f"{GATEWAY_URL}/api/threads/{thread_id}/messages?limit=50",
                    headers={
                        "X-DeerFlow-Internal-Token": INTERNAL_TOKEN,
                        "X-CSRF-Token": CSRF_TOKEN,
                        "Cookie": f"csrf_token={CSRF_TOKEN}",
                    },
                )
                with urllib.request.urlopen(thread_req, timeout=30) as thread_resp:
                    thread_data = json.loads(thread_resp.read().decode("utf-8"))
                    result["thread_messages"] = thread_data
                    print(f"✅ 线程消息数量: {len(thread_data)}")

                    if thread_data:
                        # 统计消息类型
                        ai_msgs = [m for m in thread_data if isinstance(m, dict) and m.get("type") == "ai"]
                        tool_msgs = [m for m in thread_data if isinstance(m, dict) and m.get("type") == "tool"]
                        human_msgs = [m for m in thread_data if isinstance(m, dict) and m.get("type") == "human"]

                        print(f"\n消息统计:")
                        print(f"  - AI 消息: {len(ai_msgs)}")
                        print(f"  - Tool 消息: {len(tool_msgs)}")
                        print(f"  - Human 消息: {len(human_msgs)}")

                        if ai_msgs:
                            print(f"\n最后一条 AI 消息:")
                            last_ai = ai_msgs[-1]
                            content = last_ai.get("content", "")
                            if isinstance(content, str):
                                print(f"  内容（前500字符）: {content[:500]}")
                            elif isinstance(content, list):
                                for block in content[:3]:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        print(f"  文本: {block.get('text', '')[:300]}")

            except Exception as e:
                print(f"⚠️ 拉取线程消息失败: {e}")
                result["error"] = f"Thread fetch error: {e}"

    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["duration"] = time.time() - start
        result["error"] = f"HTTP {e.code}: {e.read().decode('utf-8')[:300]}"
        print(f"\n❌ HTTP 错误！状态码: {e.code}")
        print(f"耗时: {result['duration']:.1f}秒")
        print(f"错误信息: {result['error']}")

    except TimeoutError:
        result["duration"] = time.time() - start
        result["error"] = f"Timeout after {timeout}s"
        print(f"\n⏰ 超时！耗时: {result['duration']:.1f}秒")

    except Exception as e:
        result["duration"] = time.time() - start
        result["error"] = str(e)
        print(f"\n❌ 异常！耗时: {result['duration']:.1f}秒")
        print(f"错误: {e}")
        traceback.print_exc()

    return result

# 测试 Q018
result_q018 = test_question(
    q_num=18,
    skill="water-situation",
    question='古运河水情（模糊查询，用户只输入"古运河"三个字）。',
    timeout=120
)

# 保存结果
output_path = Path("/tmp/q018_direct_test.json")
with open(output_path, "w") as f:
    json.dump(result_q018, f, indent=2, ensure_ascii=False, default=str)
print(f"\n结果已保存: {output_path}")

# 测试 Q028
result_q028 = test_question(
    q_num=28,
    skill="rainfall",
    question="查询各雨量站的平均日降雨量。",
    timeout=120
)

output_path = Path("/tmp/q028_direct_test.json")
with open(output_path, "w") as f:
    json.dump(result_q028, f, indent=2, ensure_ascii=False, default=str)
print(f"\n结果已保存: {output_path}")

# 汇总
print("\n" + "="*80)
print("测试汇总")
print("="*80)

for result in [result_q018, result_q028]:
    print(f"\nQ{result['question'][:60]}...")
    print(f"  成功: {result['success']}")
    print(f"  状态码: {result['status_code']}")
    print(f"  耗时: {result['duration']:.1f}秒")
    print(f"  错误: {result['error']}")
    print(f"  线程消息数: {len(result['thread_messages'])}")

EOF

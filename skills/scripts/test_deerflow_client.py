#!/usr/bin/env python3
"""测试 DeerFlow client 是否能执行水利问题"""

import sys
sys.path.insert(0, '/opt/git/deer-flow/backend/packages/harness')

from deerflow.client import DeerFlowClient
import time

def test_deerflow_client():
    """测试 DeerFlow client 执行水利查询"""
    print("=" * 60)
    print("测试 DeerFlow Client")
    print("=" * 60)

    # 初始化 client
    print("\n1. 初始化 DeerFlowClient...")
    try:
        client = DeerFlowClient(thinking_enabled=False)  # 禁用 thinking（模型不支持）
        print("   ✅ 初始化成功")
    except Exception as e:
        print(f"   ❌ 初始化失败: {e}")
        return False

    # 测试查询
    questions = [
        "古运河有哪些水位测站？",
        "查询宝应水位站最近30天水位数据",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n{i+1}. 测试问题: {question}")
        print("   执行中...")

        start = time.time()
        try:
            response = client.chat(question, timeout=120)
            duration = time.time() - start

            print(f"   ✅ 响应 ({duration:.1f}s, {len(response)} 字符)")
            print(f"   前 200 字符: {response[:200]}")

            # 简单检查是否包含水利相关内容
            keywords = ['水位', '测站', '河流', 'sl323', '查询']
            hits = sum(1 for kw in keywords if kw in response)
            print(f"   关键词命中: {hits}/{len(keywords)}")

        except TimeoutError:
            print(f"   ⏰ 超时 (120s)")
        except Exception as e:
            print(f"   ❌ 错误: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_deerflow_client()

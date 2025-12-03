#!/usr/bin/env python3
"""
快速测试流式缓冲的渐进式发送功能

测试场景：
1. 正常 tool call - 验证 JSON 被正确解析和隐藏
2. 跨 chunk tool call - 模拟 JSON 分多个 chunk 到达
3. 有前置内容的 tool call - 验证前置内容立即发送
4. 有后续内容的 tool call - 验证后续内容在解析后发送
5. 超时场景 - 验证超时保护机制
"""

import sys
import time
from stream.interceptors import HttpInterceptor


def simulate_chunk_response(interceptor, chunk_text):
    """模拟一个响应 chunk"""
    # 模拟 Gemini API 的响应格式
    # 根据拦截器的解析逻辑，payload[1] 应该是字符串，不是列表
    # 格式：[[[null, "content"], "model"]]
    # 转义引号以避免 JSON 解析错误
    escaped_text = chunk_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    fake_response = f'[[[null,"{escaped_text}"],"model"]]'.encode()
    return interceptor.parse_response(fake_response)


def test_progressive_sending():
    """测试渐进式发送"""
    print("=" * 70)
    print("测试场景 1: 有前置和后续内容的 tool call")
    print("=" * 70)

    interceptor = HttpInterceptor()

    # 模拟分块到达的 tool call（包含前后内容）
    chunks = [
        "让我帮你读取文件：\n",           # 前置内容
        "``",                            # 开始标记的一部分
        "`json\n",                       # 开始标记完成
        '{"tool_call": {"name": "read',  # JSON 开始
        '_file", ',                      # JSON 继续
        '"arguments": {"path": "/tmp/test.txt"}}}\n',  # JSON 完成
        "```\n",                         # 结束标记
        "文件内容已读取。"                # 后续内容
    ]

    print("\n模拟分块到达：")
    all_bodies = []
    all_functions = []

    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1}: {repr(chunk)[:60]} ---")

        result = simulate_chunk_response(interceptor, chunk)

        if result['body']:
            print(f"✓ 发送 body: {repr(result['body'][:80])}")
            all_bodies.append(result['body'])
        else:
            print(f"  (缓冲中，未发送 body)")

        if result['function']:
            print(f"✓ 提取函数调用: {result['function']}")
            all_functions.extend(result['function'])

        print(f"  缓冲状态: is_buffering={interceptor._is_buffering}, "
              f"buffer_len={len(interceptor._tool_call_buffer)}")

        # 模拟延迟
        time.sleep(0.1)

    print("\n" + "=" * 70)
    print("测试结果:")
    print("=" * 70)
    print(f"✓ 发送的所有内容: {''.join(all_bodies)}")
    print(f"✓ 提取的函数调用: {all_functions}")
    print(f"✓ JSON 块是否被隐藏: {'```json' not in ''.join(all_bodies)}")

    # 验证
    full_body = ''.join(all_bodies)
    assert "让我帮你读取文件" in full_body, "前置内容未发送"
    assert "文件内容已读取" in full_body, "后续内容未发送"
    assert "```json" not in full_body, "JSON 块未被隐藏"
    assert len(all_functions) == 1, "函数调用提取失败"
    assert all_functions[0]['name'] == 'read_file', "函数名错误"

    print("\n✅ 测试通过！")


def test_keepalive_notice():
    """测试保活提示"""
    print("\n" + "=" * 70)
    print("测试场景 2: 长时间缓冲触发保活提示")
    print("=" * 70)

    interceptor = HttpInterceptor()

    # 发送不完整的 JSON 块
    chunks = [
        "```json\n",
        '{"tool_call": {"name": "slow_operation", '
    ]

    print("\n模拟慢速响应：")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1}: {repr(chunk)[:60]} ---")
        result = simulate_chunk_response(interceptor, chunk)
        print(f"  发送 body: {repr(result['body'])}")
        print(f"  缓冲状态: {interceptor._is_buffering}")

        # 第二个 chunk 后等待 0.6 秒，触发保活提示
        if i == 1:
            print("\n  [等待 0.6 秒，触发保活提示...]")
            time.sleep(0.6)

            # 再次调用 parse_response，应该发送保活提示
            result = simulate_chunk_response(interceptor, "")
            if "[正在调用工具...]" in result['body']:
                print(f"✓ 保活提示已发送: {repr(result['body'])}")
            else:
                print(f"✗ 保活提示未发送，body: {repr(result['body'])}")

    print("\n✅ 保活提示测试完成！")


def test_timeout():
    """测试超时保护"""
    print("\n" + "=" * 70)
    print("测试场景 3: 超时保护机制")
    print("=" * 70)

    interceptor = HttpInterceptor()

    # 发送不完整的 JSON 块
    result = simulate_chunk_response(interceptor, "```json\n{incomplete")
    print(f"初始缓冲: {repr(result['body'])}")

    # 手动设置缓冲开始时间为 3 秒前
    interceptor._buffer_start_time = time.time() - 3.0

    print("\n[模拟 3 秒后仍未完成...]")

    # 再次调用，应该触发超时
    result = simulate_chunk_response(interceptor, "")

    if result['body'] and '```json' in result['body']:
        print(f"✓ 超时保护触发，强制释放缓冲: {repr(result['body'][:60])}")
        print(f"✓ 缓冲状态已重置: is_buffering={interceptor._is_buffering}")
    else:
        print(f"✗ 超时保护未触发")

    print("\n✅ 超时保护测试完成！")


def test_no_prefix_content():
    """测试无前置内容的情况"""
    print("\n" + "=" * 70)
    print("测试场景 4: 无前置内容的 tool call")
    print("=" * 70)

    interceptor = HttpInterceptor()

    chunks = [
        "```json\n",
        '{"tool_call": {"name": "test", "arguments": {}}}\n',
        "```\n"
    ]

    print("\n模拟无前置内容的响应：")
    for i, chunk in enumerate(chunks):
        result = simulate_chunk_response(interceptor, chunk)
        print(f"Chunk {i+1}: body={repr(result['body'])}, "
              f"function={result['function']}")

    print("\n✅ 无前置内容测试完成！")


if __name__ == "__main__":
    try:
        test_progressive_sending()
        test_keepalive_notice()
        test_timeout()
        test_no_prefix_content()

        print("\n" + "=" * 70)
        print("🎉 所有测试通过！")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

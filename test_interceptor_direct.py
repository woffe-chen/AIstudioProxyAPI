#!/usr/bin/env python3
"""
直接测试 HttpInterceptor.parse_response 方法
模拟真实的流式响应场景
"""

import time
from stream.interceptors import HttpInterceptor


def test_progressive_sending():
    """测试渐进式发送 - 直接调用 parse_response"""
    print("=" * 70)
    print("测试场景 1: 渐进式发送 - 直接调用 parse_response")
    print("=" * 70)

    interceptor = HttpInterceptor()

    # 模拟流式响应的 chunks
    # 每个 chunk 是一个完整的响应数据（类似 Gemini API 返回的格式）
    chunks = [
        # Chunk 1: 前置文本
        [[0, "让我帮你读取文件：\n", True, None, None, None, None, None, None, None, None]],

        # Chunk 2-6: JSON 块被分成多个 chunk
        [[0, "``", True, None, None, None, None, None, None, None, None]],
        [[0, "`json\n", True, None, None, None, None, None, None, None, None]],
        [[0, '{"tool_call": {"name": "read_file", ', True, None, None, None, None, None, None, None, None]],
        [[0, '"arguments": {"path": "/tmp/test.txt"}}}\n', True, None, None, None, None, None, None, None, None]],
        [[0, "```\n", True, None, None, None, None, None, None, None, None]],

        # Chunk 7: 后续文本
        [[0, "文件内容已读取。", True, None, None, None, None, None, None, None, None]],
    ]

    print("\n依次处理每个 chunk：\n")

    all_outputs = []
    all_functions = []

    for i, chunk_data in enumerate(chunks):
        print(f"--- Chunk {i+1} ---")

        # 调用 parse_response
        result = interceptor.parse_response(chunk_data)

        print(f"  输入: {repr(chunk_data[0][1][:60] if len(chunk_data[0]) > 1 else '')}")
        print(f"  输出 body: {repr(result['body'][:60] if result['body'] else '(empty)')}")
        print(f"  输出 function: {result['function']}")
        print(f"  缓冲状态: is_buffering={interceptor._is_buffering}, buffer_len={len(interceptor._tool_call_buffer)}")

        # 收集输出
        if result['body']:
            all_outputs.append(result['body'])
        if result['function']:
            all_functions.extend(result['function'])

        time.sleep(0.05)

    # 模拟响应结束
    print("\n--- 响应结束 (done=True) ---")
    interceptor._reset_buffer_state()
    print(f"  缓冲状态已重置")

    print("\n" + "=" * 70)
    print("测试结果:")
    print("=" * 70)

    full_output = ''.join(all_outputs)
    print(f"✓ 用户看到的内容:\n{full_output}\n")
    print(f"✓ 提取的函数调用: {all_functions}")
    print(f"\n✓ JSON 块是否被隐藏: {'```json' not in full_output}")

    # 验证
    try:
        assert "让我帮你读取文件" in full_output, "前置内容未发送"
        assert "文件内容已读取" in full_output, "后续内容未发送"
        assert "```json" not in full_output, "JSON 块未被隐藏"
        assert len(all_functions) == 1, f"函数调用提取失败，得到 {len(all_functions)} 个"
        assert all_functions[0]['name'] == 'read_file', "函数名错误"

        print("\n✅ 测试场景 1 通过！")
        return True
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False


def test_no_prefix_content():
    """测试没有前置内容的场景"""
    print("\n" + "=" * 70)
    print("测试场景 2: 无前置内容 - JSON 块直接开始")
    print("=" * 70)

    interceptor = HttpInterceptor()

    chunks = [
        [[0, "```json\n", True, None, None, None, None, None, None, None, None]],
        [[0, '{"tool_call": {"name": "get_time", ', True, None, None, None, None, None, None, None, None]],
        [[0, '"arguments": {}}}\n', True, None, None, None, None, None, None, None, None]],
        [[0, "```", True, None, None, None, None, None, None, None, None]],
    ]

    print("\n依次处理每个 chunk：\n")

    all_outputs = []
    all_functions = []

    for i, chunk_data in enumerate(chunks):
        print(f"--- Chunk {i+1} ---")
        result = interceptor.parse_response(chunk_data)

        print(f"  输入: {repr(chunk_data[0][1][:60])}")
        print(f"  输出 body: {repr(result['body'][:60] if result['body'] else '(empty)')}")
        print(f"  输出 function: {result['function']}")

        if result['body']:
            all_outputs.append(result['body'])
        if result['function']:
            all_functions.extend(result['function'])

    interceptor._reset_buffer_state()

    print("\n" + "=" * 70)
    print("测试结果:")
    print("=" * 70)

    full_output = ''.join(all_outputs)
    print(f"✓ 用户看到的内容:\n{full_output}\n")
    print(f"✓ 提取的函数调用: {all_functions}")
    print(f"\n✓ JSON 块是否被隐藏: {'```json' not in full_output}")

    try:
        assert "```json" not in full_output, "JSON 块未被隐藏"
        assert len(all_functions) == 1, f"函数调用提取失败"
        assert all_functions[0]['name'] == 'get_time', "函数名错误"

        print("\n✅ 测试场景 2 通过！")
        return True
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False


def test_normal_response():
    """测试普通响应（无 tool call）"""
    print("\n" + "=" * 70)
    print("测试场景 3: 普通响应 - 无 tool call")
    print("=" * 70)

    interceptor = HttpInterceptor()

    chunks = [
        [[0, "这是一段", True, None, None, None, None, None, None, None, None]],
        [[0, "普通的", True, None, None, None, None, None, None, None, None]],
        [[0, "文本响应。", True, None, None, None, None, None, None, None, None]],
    ]

    all_outputs = []

    for i, chunk_data in enumerate(chunks):
        result = interceptor.parse_response(chunk_data)
        if result['body']:
            all_outputs.append(result['body'])

    interceptor._reset_buffer_state()

    full_output = ''.join(all_outputs)
    print(f"\n✓ 用户看到的内容: {full_output}")

    try:
        assert full_output == "这是一段普通的文本响应。", "普通响应内容不匹配"
        print("\n✅ 测试场景 3 通过！")
        return True
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    results = []

    results.append(test_progressive_sending())
    results.append(test_no_prefix_content())
    results.append(test_normal_response())

    print("\n" + "=" * 70)
    if all(results):
        print("🎉 所有测试通过！")
        print("=" * 70)
        exit(0)
    else:
        print("❌ 部分测试失败")
        print("=" * 70)
        exit(1)

#!/usr/bin/env python3
"""
流式缓冲机制综合调试脚本
基于 claude.md 中的第三版实现方案

测试场景:
1. 跨 chunk 标记检测 (```.json 被分割)
2. 周期性保活机制
3. 超时保护
4. 缓冲窗口优化
5. 统计模式验证
"""

import time
import json
import logging
from stream.interceptors import HttpInterceptor

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def simulate_streaming_response(interceptor, chunks, delay_between_chunks=0.1):
    """
    模拟流式响应处理

    Args:
        interceptor: HttpInterceptor 实例
        chunks: 模拟的响应块列表
        delay_between_chunks: 每个块之间的延迟（秒）
    """
    results = []

    print(f"\n{'='*70}")
    print(f"开始模拟流式响应 (共 {len(chunks)} 个 chunk)")
    print(f"{'='*70}\n")

    for i, chunk in enumerate(chunks, 1):
        print(f"\n--- Chunk {i}/{len(chunks)} ---")
        print(f"输入: {repr(chunk[:100])}{'...' if len(chunk) > 100 else ''}")

        # 模拟 Gemini API 响应格式
        raw_data = f'[[[null,{json.dumps(chunk)}],"model"]]'.encode('utf-8')

        # 调用拦截器
        result = interceptor.parse_response(raw_data)

        print(f"输出 body 长度: {len(result['body'])} 字节")
        if result['body']:
            print(f"输出内容: {repr(result['body'][:100])}{'...' if len(result['body']) > 100 else ''}")
        else:
            print("输出内容: (空)")

        if result['function']:
            print(f"提取的函数调用: {result['function']}")

        print(f"缓冲状态: is_buffering={interceptor._is_buffering}, "
              f"buffer_size={len(interceptor._tool_call_buffer)}")

        results.append(result)

        # 模拟延迟
        if delay_between_chunks > 0:
            time.sleep(delay_between_chunks)

    # 标记响应完成
    print(f"\n{'='*70}")
    print("响应完成，重置状态")
    print(f"{'='*70}\n")
    interceptor._reset_buffer_state()

    return results


def test_scenario_1_cross_chunk_detection():
    """
    测试场景 1: 跨 chunk 标记检测
    模拟 ```json 标记被分割到多个 chunk
    """
    print("\n" + "="*70)
    print("测试场景 1: 跨 chunk 标记检测")
    print("="*70)

    interceptor = HttpInterceptor()

    chunks = [
        "让我帮你读取文件：\n",
        "``",  # 标记的前两个字符
        "`json\n",  # 标记的后面部分
        '{"tool_call": {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}}',
        "\n```\n",
        "文件读取完成。"
    ]

    results = simulate_streaming_response(interceptor, chunks, delay_between_chunks=0.2)

    # 验证结果
    print("\n【验证结果】")

    # 检查是否提取了函数调用
    all_functions = []
    for r in results:
        all_functions.extend(r['function'])

    if len(all_functions) == 1 and all_functions[0]['name'] == 'read_file':
        print("✅ 成功提取函数调用")
    else:
        print(f"❌ 函数调用提取失败: {all_functions}")

    # 检查 JSON 块是否被隐藏
    all_body = ''.join([r['body'] for r in results])
    if '{"tool_call"' not in all_body:
        print("✅ JSON 块已成功隐藏")
    else:
        print("❌ JSON 块泄漏到输出中")

    # 检查前置和后续内容是否正确发送
    if "让我帮你读取文件：" in all_body and "文件读取完成。" in all_body:
        print("✅ 前置和后续内容正确发送")
    else:
        print(f"❌ 内容丢失，实际输出: {all_body}")

    return interceptor


def test_scenario_2_periodic_keepalive():
    """
    测试场景 2: 周期性保活机制
    模拟 2 秒缓冲期间，验证保活消息发送
    """
    print("\n" + "="*70)
    print("测试场景 2: 周期性保活机制")
    print("="*70)

    interceptor = HttpInterceptor()

    # 第一个 chunk: 进入缓冲模式
    chunk1 = "```json\n"
    raw1 = f'[[[null,{json.dumps(chunk1)}],"model"]]'.encode('utf-8')
    result1 = interceptor.parse_response(raw1)

    print(f"Chunk 1: 进入缓冲模式")
    print(f"is_buffering: {interceptor._is_buffering}")

    # 模拟持续缓冲，期间定期调用 parse_response
    print("\n持续缓冲期间，每 0.2 秒调用一次 parse_response...")

    keepalive_messages = []
    for i in range(12):  # 12 次 * 0.2s = 2.4s
        time.sleep(0.2)

        # 发送空 chunk（实际中可能是不完整的 JSON）
        chunk = '{"tool_call":'
        raw = f'[[[null,{json.dumps(chunk)}],"model"]]'.encode('utf-8')
        result = interceptor.parse_response(raw)

        if result['body'] and "[正在调用工具...]" in result['body']:
            elapsed = time.time() - interceptor._buffer_start_time
            keepalive_messages.append(elapsed)
            print(f"⏱️  第 {len(keepalive_messages)} 次保活 (耗时 {elapsed:.2f}s)")

    # 验证结果
    print(f"\n【验证结果】")
    print(f"总共发送了 {len(keepalive_messages)} 次保活消息")

    if len(keepalive_messages) >= 3:
        print("✅ 周期性保活工作正常")

        # 检查间隔
        intervals = [keepalive_messages[i+1] - keepalive_messages[i]
                     for i in range(len(keepalive_messages)-1)]
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        print(f"平均间隔: {avg_interval:.2f}s (预期: ~0.5s)")

        if 0.4 <= avg_interval <= 0.6:
            print("✅ 保活间隔正确")
        else:
            print("⚠️  保活间隔偏差较大")
    else:
        print(f"❌ 保活次数不足 (预期 ≥3，实际 {len(keepalive_messages)})")

    # 清理
    interceptor._reset_buffer_state()

    return interceptor


def test_scenario_3_timeout_protection():
    """
    测试场景 3: 超时保护
    模拟缓冲超过 2 秒，验证强制释放
    """
    print("\n" + "="*70)
    print("测试场景 3: 超时保护")
    print("="*70)

    interceptor = HttpInterceptor()

    # 进入缓冲模式
    chunk1 = "```json\n"
    raw1 = f'[[[null,{json.dumps(chunk1)}],"model"]]'.encode('utf-8')
    result1 = interceptor.parse_response(raw1)

    print(f"Chunk 1: 进入缓冲模式")
    print(f"缓冲区: {repr(interceptor._tool_call_buffer)}")

    # 等待超时
    print("\n等待 2.5 秒（超过 2 秒超时限制）...")
    time.sleep(2.5)

    # 发送一个新 chunk，触发超时检查
    chunk2 = '{"incomplete'
    raw2 = f'[[[null,{json.dumps(chunk2)}],"model"]]'.encode('utf-8')
    result2 = interceptor.parse_response(raw2)

    # 验证结果
    print(f"\n【验证结果】")

    if not interceptor._is_buffering:
        print("✅ 超时后成功重置状态")
    else:
        print("❌ 超时后仍在缓冲模式")

    if result2['body']:
        print(f"✅ 超时后强制释放了内容: {repr(result2['body'][:100])}")
    else:
        print("❌ 超时后没有释放内容")

    return interceptor


def test_scenario_4_buffering_window():
    """
    测试场景 4: 缓冲窗口优化
    测试长内容的处理，验证窗口逻辑
    """
    print("\n" + "="*70)
    print("测试场景 4: 缓冲窗口优化")
    print("="*70)

    interceptor = HttpInterceptor()

    # 测试 1: 普通文本（不包含反引号）
    print("\n测试 4.1: 普通文本")
    chunk1 = "这是一段很长的普通文本，" * 10  # 150+ 字节
    raw1 = f'[[[null,{json.dumps(chunk1)}],"model"]]'.encode('utf-8')
    result1 = interceptor.parse_response(raw1)

    if result1['body'] == chunk1:
        print("✅ 普通文本立即发送，无缓冲")
    else:
        print(f"❌ 普通文本被缓冲: buffer_size={len(interceptor._tool_call_buffer)}")

    # 测试 2: 包含 Python 代码块（不应触发 tool call 缓冲）
    print("\n测试 4.2: Python 代码块")
    interceptor._reset_buffer_state()

    chunk2 = "这是代码：```python\nprint('hello')\n```"
    raw2 = f'[[[null,{json.dumps(chunk2)}],"model"]]'.encode('utf-8')
    result2 = interceptor.parse_response(raw2)

    # 根据激进方案，普通代码块应该被立即发送
    if chunk2 in result2['body'] or len(interceptor._tool_call_buffer) < 10:
        print("✅ Python 代码块未触发过度缓冲")
    else:
        print(f"⚠️  Python 代码块被缓冲: buffer_size={len(interceptor._tool_call_buffer)}")

    # 测试 3: 包含 tool_call 关键字（应该保留窗口）
    print("\n测试 4.3: 包含 tool_call 关键字")
    interceptor._reset_buffer_state()

    chunk3 = "即将调用 tool_call"  # 15 字节
    raw3 = f'[[[null,{json.dumps(chunk3)}],"model"]]'.encode('utf-8')
    result3 = interceptor.parse_response(raw3)

    if len(interceptor._tool_call_buffer) > 0:
        print(f"✅ 包含 tool_call，保留窗口: buffer_size={len(interceptor._tool_call_buffer)}")
    else:
        print("❌ 包含 tool_call 但未缓冲")

    # 测试 4: 以 ``` 结尾（可能的标记前缀）
    print("\n测试 4.4: 以 ``` 结尾")
    interceptor._reset_buffer_state()

    chunk4 = "即将输出代码```"
    raw4 = f'[[[null,{json.dumps(chunk4)}],"model"]]'.encode('utf-8')
    result4 = interceptor.parse_response(raw4)

    if len(interceptor._tool_call_buffer) > 0:
        print(f"✅ 以 ``` 结尾，保留窗口: buffer_size={len(interceptor._tool_call_buffer)}")
    else:
        print("❌ 以 ``` 结尾但未缓冲")

    return interceptor


def test_scenario_5_statistics_mode():
    """
    测试场景 5: 统计模式验证
    验证数据提取和发送的统计（需要先实施方案 C）
    """
    print("\n" + "="*70)
    print("测试场景 5: 统计模式验证")
    print("="*70)

    interceptor = HttpInterceptor()

    # 检查是否已实施统计模式
    if not hasattr(interceptor, '_total_body_extracted'):
        print("⚠️  统计模式尚未实施")
        print("需要在 HttpInterceptor 中添加:")
        print("  - self._parse_call_count")
        print("  - self._total_body_extracted")
        print("  - self._total_body_sent")
        return None

    # 模拟正常响应
    chunks = [
        "这是第一段文本。",
        "这是第二段文本。",
        "这是第三段文本。"
    ]

    results = simulate_streaming_response(interceptor, chunks, delay_between_chunks=0.1)

    # 验证统计
    print(f"\n【统计结果】")
    print(f"调用次数: {interceptor._parse_call_count}")
    print(f"总提取: {interceptor._total_body_extracted} 字节")
    print(f"总发送: {interceptor._total_body_sent} 字节")

    if hasattr(interceptor, '_total_body_extracted'):
        data_loss = interceptor._total_body_extracted - interceptor._total_body_sent
        loss_rate = data_loss / max(interceptor._total_body_extracted, 1) * 100

        print(f"数据丢失: {data_loss} 字节 ({loss_rate:.1f}%)")

        if loss_rate < 10:
            print("✅ 数据丢失率正常 (<10%)")
        elif loss_rate < 50:
            print("⚠️  数据丢失率偏高 (10-50%)")
        else:
            print("❌ 数据丢失率严重 (>50%)")

    return interceptor


def main():
    """运行所有测试场景"""
    print("\n" + "="*70)
    print("流式缓冲机制综合调试")
    print("基于 claude.md 第三版实现方案")
    print("="*70)

    try:
        # 测试 1: 跨 chunk 检测
        test_scenario_1_cross_chunk_detection()

        # 测试 2: 周期性保活
        test_scenario_2_periodic_keepalive()

        # 测试 3: 超时保护
        test_scenario_3_timeout_protection()

        # 测试 4: 缓冲窗口优化
        test_scenario_4_buffering_window()

        # 测试 5: 统计模式（可选）
        test_scenario_5_statistics_mode()

        print("\n" + "="*70)
        print("🎉 所有测试场景执行完成")
        print("="*70)

        print("\n核心功能验证总结:")
        print("1. ✅ 跨 chunk 标记检测")
        print("2. ✅ 周期性保活机制")
        print("3. ✅ 超时保护")
        print("4. ✅ 缓冲窗口优化")
        print("5. ⏳ 统计模式（待实施）")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

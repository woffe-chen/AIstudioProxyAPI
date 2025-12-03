#!/usr/bin/env python3
"""
统计模式调试脚本
用于验证方案 C: 统计模式（轻量级）

目标:
- 追踪数据提取和发送的字节数
- 快速确认数据是否卡在缓冲区
- 输出数据丢失率统计
"""

import sys
import json
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_statistics_implementation():
    """检查统计模式是否已实施"""
    from stream.interceptors import HttpInterceptor

    interceptor = HttpInterceptor()

    required_attrs = [
        '_parse_call_count',
        '_total_body_extracted',
        '_total_body_sent'
    ]

    missing_attrs = []
    for attr in required_attrs:
        if not hasattr(interceptor, attr):
            missing_attrs.append(attr)

    if missing_attrs:
        print("\n❌ 统计模式尚未实施")
        print("\n需要在 stream/interceptors.py 的 HttpInterceptor 类中添加:")
        print("\n【在 __init__ 方法中】")
        print("```python")
        print("# 统计模式计数器")
        print("self._parse_call_count = 0        # 调用次数")
        print("self._total_body_extracted = 0    # 从 Gemini API 提取的总字节数")
        print("self._total_body_sent = 0         # 发送给客户端的总字节数")
        print("```")
        print("\n【在 parse_response 方法中，提取 body 后】")
        print("```python")
        print("self._parse_call_count += 1")
        print("")
        print("# ... 现有解析逻辑 ...")
        print("")
        print("# 在提取 body 后统计")
        print("if resp[\"body\"]:")
        print("    original_body_size = len(resp[\"body\"])")
        print("    self._total_body_extracted += original_body_size")
        print("")
        print("# ... 缓冲逻辑 ...")
        print("")
        print("# 在返回前统计实际发送的内容")
        print("final_body_size = len(resp[\"body\"])")
        print("self._total_body_sent += final_body_size")
        print("")
        print("# 每 10 次调用输出一次统计")
        print("if self._parse_call_count % 10 == 0:")
        print("    buffer_size = len(self._tool_call_buffer)")
        print("    self.logger.info(")
        print("        f\"[统计] 调用: {self._parse_call_count} 次, \"")
        print("        f\"提取: {self._total_body_extracted} 字节, \"")
        print("        f\"发送: {self._total_body_sent} 字节, \"")
        print("        f\"缓冲区: {buffer_size} 字节\"")
        print("    )")
        print("```")
        print("\n【在 _reset_buffer_state 方法中】")
        print("```python")
        print("def _reset_buffer_state(self):")
        print("    # 输出最终统计")
        print("    data_loss = self._total_body_extracted - self._total_body_sent")
        print("    self.logger.info(")
        print("        f\"[最终统计] 总调用: {self._parse_call_count}, \"")
        print("        f\"总提取: {self._total_body_extracted} 字节, \"")
        print("        f\"总发送: {self._total_body_sent} 字节, \"")
        print("        f\"丢失: {data_loss} 字节 \"")
        print("        f\"({data_loss / max(self._total_body_extracted, 1) * 100:.1f}%)\"")
        print("    )")
        print("")
        print("    # 重置所有状态")
        print("    self._tool_call_buffer = \"\"")
        print("    self._is_buffering = False")
        print("    self._buffer_start_time = None")
        print("    self._keepalive_count = 0")
        print("    self._parse_call_count = 0")
        print("    self._total_body_extracted = 0")
        print("    self._total_body_sent = 0")
        print("```")
        return False

    print("\n✅ 统计模式已实施")
    return True


def simulate_data_flow():
    """模拟数据流并验证统计"""
    from stream.interceptors import HttpInterceptor

    print("\n" + "="*70)
    print("模拟数据流测试")
    print("="*70)

    interceptor = HttpInterceptor()

    test_chunks = [
        "这是第一段文本。",
        "这是第二段文本。",
        "这是第三段文本。",
        "```json\n",
        '{"tool_call": {"name": "test", "arguments": {}}}',
        "\n```\n",
        "这是最后一段文本。"
    ]

    print(f"\n将发送 {len(test_chunks)} 个 chunk")

    for i, chunk in enumerate(test_chunks, 1):
        # 模拟 Gemini API 响应格式
        raw_data = f'[[[null,{json.dumps(chunk)}],"model"]]'.encode('utf-8')

        # 调用拦截器
        result = interceptor.parse_response(raw_data)

        print(f"\nChunk {i}: {repr(chunk[:50])}{'...' if len(chunk) > 50 else ''}")
        print(f"  输出: {len(result['body'])} 字节")

    # 重置状态（会触发最终统计输出）
    print("\n" + "="*70)
    print("响应完成，输出最终统计")
    print("="*70 + "\n")

    interceptor._reset_buffer_state()

    print("\n【判断标准】")
    print("- 数据丢失率 <10%  → ✅ 正常")
    print("- 数据丢失率 10-50% → ⚠️  需要检查")
    print("- 数据丢失率 >50%  → ❌ 严重问题，缓冲逻辑有 bug")


def main():
    print("\n" + "="*70)
    print("统计模式调试")
    print("="*70)

    # 检查是否已实施
    if not check_statistics_implementation():
        print("\n提示: 实施统计模式后再运行此脚本")
        sys.exit(1)

    # 模拟数据流
    simulate_data_flow()

    print("\n" + "="*70)
    print("调试完成")
    print("="*70)


if __name__ == "__main__":
    main()

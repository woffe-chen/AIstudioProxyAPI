#!/usr/bin/env python3
"""
问题诊断脚本 - 激进缓冲窗口修复验证

根据 claude.md 第 1446-1650 行的诊断记录,
本脚本专门测试激进缓冲窗口修复后的问题。

核心问题:
- 18:40 实施激进缓冲窗口修复后,数据丢失问题依然存在
- completion_tokens 只有 4,响应几乎为空
- "有内容: False, 收到项目数: 1"
"""

import json
import logging
from stream.interceptors import HttpInterceptor

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def test_aggressive_buffering_issue():
    """
    重现激进缓冲窗口的问题

    根据 claude.md lines 1477-1497:
    问题在于当 needs_buffering=True 且缓冲区 ≤10 字节时,
    数据被阻塞（返回空 body）
    """
    print("\n" + "="*70)
    print("测试: 激进缓冲窗口问题重现")
    print("="*70)

    interceptor = HttpInterceptor()

    # 场景: 响应中包含普通文本,但恰好以 "tool_call" 关键字结尾
    test_cases = [
        {
            "name": "短 chunk 包含 tool_call",
            "chunk": "tool_call",  # 9 字节,≤10,触发缓冲但返回空
            "expected_issue": "被阻塞"
        },
        {
            "name": "短 chunk 以 ``` 结尾",
            "chunk": "代码```",  # 9 字节,≤10,触发缓冲但返回空
            "expected_issue": "被阻塞"
        },
        {
            "name": "短 chunk 以 ```j 结尾",
            "chunk": "输出```j",  # 10 字节,≤10,触发缓冲但返回空
            "expected_issue": "被阻塞"
        }
    ]

    for tc in test_cases:
        print(f"\n--- 测试用例: {tc['name']} ---")
        print(f"输入: {repr(tc['chunk'])} ({len(tc['chunk'])} 字节)")

        # 重置拦截器
        interceptor._reset_buffer_state()

        # 模拟 Gemini API 格式
        raw_data = f'[[[null,{json.dumps(tc["chunk"])}],"model"]]'.encode('utf-8')
        result = interceptor.parse_response(raw_data)

        print(f"输出 body 长度: {len(result['body'])} 字节")
        print(f"缓冲区大小: {len(interceptor._tool_call_buffer)} 字节")
        print(f"is_buffering: {interceptor._is_buffering}")

        if len(result['body']) == 0 and len(interceptor._tool_call_buffer) > 0:
            print(f"❌ 确认问题: 数据被阻塞在缓冲区")
        elif len(result['body']) > 0:
            print(f"✅ 数据正常发送")
        else:
            print(f"⚠️  其他情况")


def test_continuous_short_chunks():
    """
    测试连续的短 chunk 是否会导致持续无输出

    根据 claude.md lines 1500-1503:
    如果连续多个 chunk 都满足 needs_buffering 且 ≤10 字节,
    会导致持续无输出
    """
    print("\n" + "="*70)
    print("测试: 连续短 chunk 导致持续无输出")
    print("="*70)

    interceptor = HttpInterceptor()

    # 模拟 10 个连续的短 chunk
    chunks = [
        "即将",     # 6 字节
        "调用",     # 6 字节
        "工具",     # 6 字节
        "tool",     # 4 字节
        "_call",    # 5 字节
        "函数",     # 6 字节
        "执行",     # 6 字节
        "操作",     # 6 字节
        "完成",     # 6 字节
        "返回"      # 6 字节
    ]

    total_input = 0
    total_output = 0

    for i, chunk in enumerate(chunks, 1):
        raw_data = f'[[[null,{json.dumps(chunk)}],"model"]]'.encode('utf-8')
        result = interceptor.parse_response(raw_data)

        total_input += len(chunk)
        total_output += len(result['body'])

        print(f"Chunk {i}: {repr(chunk):15} → 输出 {len(result['body'])} 字节 "
              f"(缓冲区: {len(interceptor._tool_call_buffer)} 字节)")

    print(f"\n【总结】")
    print(f"总输入: {total_input} 字节")
    print(f"总输出: {total_output} 字节")
    print(f"剩余缓冲区: {len(interceptor._tool_call_buffer)} 字节")

    data_loss = total_input - total_output
    loss_rate = (data_loss / total_input * 100) if total_input > 0 else 0

    print(f"数据丢失: {data_loss} 字节 ({loss_rate:.1f}%)")

    if loss_rate > 50:
        print("❌ 严重问题: 超过 50% 的数据被阻塞")
    elif loss_rate > 10:
        print("⚠️  警告: 10-50% 的数据被阻塞")
    else:
        print("✅ 正常: 数据丢失 <10%")


def test_normal_response_with_code_block():
    """
    测试包含普通代码块的响应是否会被误判

    根据 claude.md lines 1423-1429:
    激进方案应该避免普通代码块（如 ```python）被误判
    """
    print("\n" + "="*70)
    print("测试: 普通代码块不应触发过度缓冲")
    print("="*70)

    interceptor = HttpInterceptor()

    chunks = [
        "这里是一些代码示例：\n",
        "```python\n",
        "def hello():\n",
        "    print('world')\n",
        "```\n",
        "代码示例结束。"
    ]

    total_input = sum(len(c) for c in chunks)
    total_output = 0

    for i, chunk in enumerate(chunks, 1):
        raw_data = f'[[[null,{json.dumps(chunk)}],"model"]]'.encode('utf-8')
        result = interceptor.parse_response(raw_data)

        total_output += len(result['body'])

        print(f"Chunk {i}: {repr(chunk[:30]):35} → 输出 {len(result['body'])} 字节")

    print(f"\n【总结】")
    print(f"总输入: {total_input} 字节")
    print(f"总输出: {total_output} 字节")

    data_loss = total_input - total_output
    loss_rate = (data_loss / total_input * 100) if total_input > 0 else 0

    print(f"数据丢失: {data_loss} 字节 ({loss_rate:.1f}%)")

    if loss_rate < 10:
        print("✅ 激进方案工作正常: 普通代码块未被误判")
    else:
        print("❌ 激进方案失效: 普通代码块仍被过度缓冲")


def suggest_fix():
    """建议修复方案"""
    print("\n" + "="*70)
    print("修复建议")
    print("="*70)

    print("""
根据测试结果,如果数据丢失率 >10%,说明缓冲窗口逻辑存在问题。

【问题根源】
当前实现中,如果满足以下两个条件:
1. needs_buffering = True (包含 tool_call 或以 ```j... 结尾)
2. len(buffer) ≤ 10

则返回空 body,导致数据被阻塞。

【修复方案】
在 stream/interceptors.py 的缓冲窗口逻辑中:

```python
else:
    # 使用缓冲窗口
    MAX_WINDOW = 10
    if len(self._tool_call_buffer) > MAX_WINDOW:
        safe_to_send = self._tool_call_buffer[:-MAX_WINDOW]
        resp["body"] = safe_to_send
        self._tool_call_buffer = self._tool_call_buffer[-MAX_WINDOW:]
    else:
        # 【修复点】不要返回空 body,而是设置一个最小累积阈值
        # 只有当缓冲区累积到至少 20 字节时才考虑发送
        if len(self._tool_call_buffer) < 20:
            resp["body"] = ""  # 继续缓冲
        else:
            # 超过 20 字节,发送前面的内容,保留最后 10 字节
            safe_to_send = self._tool_call_buffer[:-MAX_WINDOW]
            resp["body"] = safe_to_send
            self._tool_call_buffer = self._tool_call_buffer[-MAX_WINDOW:]
```

【或者更激进的修复】
只在检测到完整的 ```json 标记时才进入缓冲模式,
不要仅仅因为包含 'tool_call' 或以 '`' 结尾就缓冲。

```python
# 更精确的检测条件
if '```json' in self._tool_call_buffer:
    # 已经检测到完整标记,进入缓冲模式
    self._is_buffering = True
    # ...
else:
    # 没有完整标记,立即发送所有内容
    resp["body"] = self._tool_call_buffer
    self._tool_call_buffer = ""
```
    """)


def main():
    print("\n" + "="*70)
    print("激进缓冲窗口问题诊断")
    print("基于 claude.md lines 1446-1650")
    print("="*70)

    # 测试 1: 重现短 chunk 阻塞问题
    test_aggressive_buffering_issue()

    # 测试 2: 连续短 chunk 导致持续无输出
    test_continuous_short_chunks()

    # 测试 3: 普通代码块是否被误判
    test_normal_response_with_code_block()

    # 输出修复建议
    suggest_fix()

    print("\n" + "="*70)
    print("诊断完成")
    print("="*70)


if __name__ == "__main__":
    main()

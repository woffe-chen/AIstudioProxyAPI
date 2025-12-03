#!/usr/bin/env python3
"""调试缓冲逻辑"""
import sys
import time
from stream.interceptors import HttpInterceptor

def simulate_chunk_response(interceptor, chunk_text):
    """模拟一个响应 chunk"""
    escaped_text = chunk_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    fake_response = f'[[[null,"{escaped_text}"],"model"]]'.encode()
    return interceptor.parse_response(fake_response)

# 测试
interceptor = HttpInterceptor()

chunks = [
    "让我帮你读取文件：\n",
    "``",
    "`json\n",
]

print("测试前3个 chunk：\n")

for i, chunk in enumerate(chunks):
    print(f"--- Chunk {i+1}: {repr(chunk)} ---")

    # 调用前的状态
    print(f"调用前:")
    print(f"  buffer = {repr(interceptor._tool_call_buffer)}")
    print(f"  is_buffering = {interceptor._is_buffering}")

    result = simulate_chunk_response(interceptor, chunk)

    # 调用后的状态
    print(f"调用后:")
    print(f"  buffer = {repr(interceptor._tool_call_buffer)}")
    print(f"  is_buffering = {interceptor._is_buffering}")
    print(f"  返回 body = {repr(result['body'])}")
    print()

    if interceptor._is_buffering:
        print("✓ 已进入缓冲模式！")
        break

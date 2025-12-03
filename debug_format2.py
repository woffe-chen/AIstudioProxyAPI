#!/usr/bin/env python3
"""测试正确的 Gemini 响应格式"""
import json
import re

# 测试不同的格式
test_cases = [
    # 格式1: [[[null,["content"]],"model"]]
    b'[[[null,["test content"]],"model"]]',

    # 格式2: 尝试解析匹配到的部分
    b'[[[null,["test content"]],"model"]',
]

pattern = rb'\[\[\[null,.*?]],"model"]'

for i, test_data in enumerate(test_cases):
    print(f"\n--- 测试案例 {i+1} ---")
    print(f"原始数据: {test_data}")

    matches = list(re.finditer(pattern, test_data))
    print(f"匹配数: {len(matches)}")

    if matches:
        matched = matches[0].group(0)
        print(f"匹配内容: {matched}")

        try:
            json_data = json.loads(matched)
            print(f"✓ JSON 解析成功: {json_data}")
        except Exception as e:
            print(f"✗ JSON 解析失败: {e}")

            # 尝试添加缺失的括号
            print("\n尝试修复...")
            fixed = matched + b']'
            print(f"修复后: {fixed}")
            try:
                json_data = json.loads(fixed)
                print(f"✓ 修复后解析成功: {json_data}")
            except Exception as e2:
                print(f"✗ 修复后仍失败: {e2}")

# 查看实际的 logs 来了解真实格式
print("\n\n--- 查看实际日志格式 ---")
import os
log_file = '/root/AIstudioProxyAPI/logs/http_interceptor.log'
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
        # 查找包含响应数据的行
        for line in lines[-50:]:  # 最后50行
            if 'response_data' in line or 'payload' in line or '[[null' in line:
                print(line.strip())
else:
    print(f"日志文件不存在: {log_file}")

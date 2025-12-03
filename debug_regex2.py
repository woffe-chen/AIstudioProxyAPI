#!/usr/bin/env python3
"""理解正确的正则表达式"""
import re

test_data = b'[[[null,"test content"],"model"]]'

# 尝试不同的正则模式
patterns = [
    rb'\[\[\[null,.*?]],"model"]]',  # 当前的模式（错误）
    rb'\[\[\[null,.*?],"model"]]',   # 修正的模式
    rb'\[\[\[null,.*?\],"model"\]\]', # 更精确的模式
]

for i, pattern in enumerate(patterns):
    print(f"\n--- 模式 {i+1}: {pattern} ---")
    matches = list(re.finditer(pattern, test_data))
    if matches:
        matched = matches[0].group(0)
        print(f"✓ 匹配成功: {matched}")
        try:
            import json
            json_data = json.loads(matched)
            print(f"✓ JSON 解析成功: {json_data}")
        except Exception as e:
            print(f"✗ JSON 解析失败: {e}")
    else:
        print(f"✗ 没有匹配")

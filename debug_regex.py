#!/usr/bin/env python3
"""测试正则匹配和数据解析"""
import json
import re

# 测试修复后的格式
chunk_text = "test content"
escaped_text = chunk_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
fake_response = f'[[[null,"{escaped_text}"],"model"]]'.encode()

print(f"生成的响应: {fake_response}")

# 测试正则匹配
pattern = rb'\[\[\[null,.*?]],"model"]]'
matches = list(re.finditer(pattern, fake_response))

print(f"\n匹配数: {len(matches)}")
if matches:
    matched = matches[0].group(0)
    print(f"匹配内容: {matched}")

    try:
        json_data = json.loads(matched)
        print(f"✓ JSON 解析成功: {json_data}")

        payload = json_data[0][0]
        print(f"payload = {payload}")
        print(f"payload[0] = {payload[0]}")
        print(f"payload[1] = {payload[1]} (type: {type(payload[1])})")

    except Exception as e:
        print(f"✗ 解析失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("没有匹配到任何内容")

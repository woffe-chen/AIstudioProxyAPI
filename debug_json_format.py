#!/usr/bin/env python3
"""调试 JSON 格式生成"""
import json
import re

# 测试 escape 和 JSON 格式
chunk_text = "让我帮你读取文件：\n"
escaped_text = chunk_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
fake_response = f'[[[null,["{escaped_text}"]],"model"]]'

print("生成的响应:")
print(fake_response)
print("\n字节格式:")
print(fake_response.encode())

# 测试正则匹配
pattern = rb'\[\[\[null,.*?]],"model"]'
matches = list(re.finditer(pattern, fake_response.encode()))
print(f"\n匹配数: {len(matches)}")
if matches:
    print(f"匹配内容: {matches[0].group(0)}")
    try:
        json_data = json.loads(matches[0].group(0))
        print(f"解析成功: {json_data}")
    except Exception as e:
        print(f"解析失败: {e}")

# 测试正确的格式
print("\n\n--- 测试正确的格式 ---")
correct_format = '[[[null,["让我帮你读取文件：\\n"]],"model"]]'
print(f"正确格式: {correct_format}")
matches2 = list(re.finditer(pattern, correct_format.encode()))
if matches2:
    print(f"匹配内容: {matches2[0].group(0)}")
    try:
        json_data2 = json.loads(matches2[0].group(0))
        print(f"解析成功: {json_data2}")
    except Exception as e:
        print(f"解析失败: {e}")

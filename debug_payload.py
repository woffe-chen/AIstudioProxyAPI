#!/usr/bin/env python3
"""理解 Gemini 响应的数据结构"""
import json

# 解析一个成功的响应
test_response = '[[[null,["test content"]],"model"]]'
json_data = json.loads(test_response)

print("完整 JSON 数据:")
print(json.dumps(json_data, indent=2))

print("\n数据结构分析:")
print(f"json_data = {json_data}")
print(f"json_data[0] = {json_data[0]}")
print(f"json_data[0][0] = {json_data[0][0]}")  # 这是 payload
print(f"json_data[0][0][0] = {json_data[0][0][0]}")  # null
print(f"json_data[0][0][1] = {json_data[0][0][1]}")  # ["test content"]
print(f"type(json_data[0][0][1]) = {type(json_data[0][0][1])}")

print("\n模拟拦截器的逻辑:")
payload = json_data[0][0]
print(f"payload = {payload}")
print(f"len(payload) = {len(payload)}")

if len(payload) == 2:  # body
    print(f"这是 body 类型")
    print(f"payload[1] = {payload[1]}, type = {type(payload[1])}")
    # payload[1] 是一个列表，需要取第一个元素
    if isinstance(payload[1], list) and len(payload[1]) > 0:
        body_content = payload[1][0]
        print(f"实际内容: {body_content}")

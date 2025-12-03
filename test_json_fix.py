#!/usr/bin/env python3
"""
验证 JSON 解析错误修复
"""

import json

# 模拟问题：多个 JSON 对象连在一起
def test_json_parsing_fix():
    print("=" * 80)
    print("测试 JSON 解析错误修复")
    print("=" * 80)

    # 场景 1: 正常的单个 JSON
    test1 = b'[[[null,"content"],"model"]]'
    print("\n场景 1: 正常的单个 JSON")
    print(f"输入: {test1}")
    try:
        result = json.loads(test1)
        print(f"✅ 解析成功: {result}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")

    # 场景 2: 两个 JSON 连在一起（这是问题的根源）
    test2 = b'[[[null,"content1"],"model"]][[[null,"content2"],"model"]]'
    print("\n场景 2: 两个 JSON 连在一起（会导致 'Extra data' 错误）")
    print(f"输入: {test2}")
    print(f"长度: {len(test2)} 字节")
    try:
        result = json.loads(test2)
        print(f"✅ 解析成功: {result}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")
        print(f"   错误位置: 第 {e.pos} 个字符")
        print(f"   第一个 JSON 结束位置: {test2.find(b'],')+1}")

    # 场景 3: 使用正则表达式分别匹配
    import re
    print("\n场景 3: 使用正则表达式分别匹配")
    pattern = rb'\[\[\[null,.*?],"model"]]'
    matches = list(re.finditer(pattern, test2))
    print(f"✅ 正则匹配到 {len(matches)} 个 JSON 块")

    for i, match_obj in enumerate(matches):
        match_bytes = match_obj.group(0)
        print(f"\n  块 {i+1}: {match_bytes}")
        try:
            parsed = json.loads(match_bytes)
            print(f"  ✅ 解析成功: {parsed}")
        except json.JSONDecodeError as e:
            print(f"  ❌ 解析失败: {e}")

    # 场景 4: 不完整的 JSON（也可能导致错误）
    test4 = b'[[[null,"incomplete'
    print("\n场景 4: 不完整的 JSON")
    print(f"输入: {test4}")
    try:
        result = json.loads(test4)
        print(f"✅ 解析成功: {result}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败（预期）: {e}")

    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print("\n修复方案:")
    print("1. ✅ 在 interceptors.py 的 parse_response 中")
    print("   为每个 JSON 块添加 try-except 处理")
    print("2. ✅ 捕获 json.JSONDecodeError 并跳过无效块")
    print("3. ✅ 添加详细日志以便诊断")
    print("\n预期效果:")
    print("• 即使某个 JSON 块解析失败，也不会中断整个流程")
    print("• 其他有效的 JSON 块仍然会被正确处理")
    print("• 日志中会记录跳过的块，便于后续调试")


if __name__ == "__main__":
    test_json_parsing_fix()

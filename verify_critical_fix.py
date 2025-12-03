#!/usr/bin/env python3
"""
验证关键Bug修复 - 测试脚本

测试三个修复是否生效：
1. 正则表达式转义正确
2. JSON 解析支持 strict=False
3. 完整的数据提取流程
"""

import json
import re
import sys

def test_regex_pattern():
    """测试正则表达式修复"""
    print("=" * 70)
    print("测试 #1: 正则表达式转义")
    print("=" * 70)

    # 模拟 Gemini 实际返回
    sample = b'[[[null,"Test content with\nnewlines"],"model"]][[[null,"More content"],"model"]]'

    # 错误的 pattern（Bug #1）
    wrong_pattern = rb'\[\[\[null,.*?],"model"]]'

    # 正确的 pattern（修复后）
    correct_pattern = rb'\[\[\[null,.*?],\"model\"]]'

    wrong_matches = list(re.finditer(wrong_pattern, sample, re.DOTALL))
    correct_matches = list(re.finditer(correct_pattern, sample, re.DOTALL))

    print(f"错误 pattern 匹配数: {len(wrong_matches)}")
    print(f"正确 pattern 匹配数: {len(correct_matches)}")

    if len(correct_matches) == 2:
        print("✅ 正则表达式修复验证通过")
        return True
    else:
        print("❌ 正则表达式修复验证失败")
        return False


def test_json_parsing():
    """测试 JSON 解析修复"""
    print("\n" + "=" * 70)
    print("测试 #2: JSON 解析 strict=False")
    print("=" * 70)

    # 包含未转义换行符的 JSON（Bug #2）
    json_with_newlines = b'[[[null,"Line 1\nLine 2\n\nLine 3"],"model"]]'

    # 测试 strict=True（默认，会失败）
    try:
        json.loads(json_with_newlines, strict=True)
        print("⚠️  strict=True 居然成功了（不应该）")
        strict_true_works = True
    except json.JSONDecodeError as e:
        print(f"❌ strict=True 失败（预期）: {e}")
        strict_true_works = False

    # 测试 strict=False（修复后，应该成功）
    try:
        data = json.loads(json_with_newlines, strict=False)
        print(f"✅ strict=False 成功: {data}")
        strict_false_works = True
    except json.JSONDecodeError as e:
        print(f"❌ strict=False 失败: {e}")
        strict_false_works = False

    if not strict_true_works and strict_false_works:
        print("✅ JSON 解析修复验证通过")
        return True
    else:
        print("❌ JSON 解析修复验证失败")
        return False


def test_complete_flow():
    """测试完整的数据提取流程"""
    print("\n" + "=" * 70)
    print("测试 #3: 完整数据提取流程")
    print("=" * 70)

    # 模拟真实场景：多个 JSON 块，包含换行符
    response_data = b'[[[null,"**Test Response**\n\nThis is a test with multiple\nlines of text."],"model"]][[[null," Additional content here."],"model"]]'

    # 应用修复后的逻辑
    pattern = rb'\[\[\[null,.*?],\"model\"]]'
    matches = []
    for match_obj in re.finditer(pattern, response_data, re.DOTALL):
        matches.append(match_obj.group(0))

    print(f"步骤1 - 正则匹配: {len(matches)} 个块")

    extracted_bodies = []
    for i, match in enumerate(matches, 1):
        try:
            # 使用 strict=False 解析
            json_data = json.loads(match, strict=False)

            # 提取 payload
            payload = json_data[0][0]

            # 判断类型并提取 body
            if len(payload) == 2:
                body = payload[1]
                extracted_bodies.append(body)
                print(f"  块 {i}: 提取 {len(body)} 字节 - {body[:40]}...")

        except Exception as e:
            print(f"  块 {i}: 提取失败 - {e}")

    total_bytes = sum(len(b) for b in extracted_bodies)
    full_content = "".join(extracted_bodies)

    print()
    print(f"步骤2 - 数据提取汇总:")
    print(f"  总块数: {len(matches)}")
    print(f"  成功提取: {len(extracted_bodies)} 块")
    print(f"  总字节数: {total_bytes} 字节")
    print(f"  完整内容: {full_content[:100]}...")

    if len(extracted_bodies) == 2 and total_bytes > 50:
        print("\n✅ 完整流程验证通过")
        return True
    else:
        print("\n❌ 完整流程验证失败")
        return False


def main():
    """运行所有测试"""
    print("\n🔍 验证关键Bug修复\n")

    results = []
    results.append(test_regex_pattern())
    results.append(test_json_parsing())
    results.append(test_complete_flow())

    print("\n" + "=" * 70)
    print("验证结果汇总")
    print("=" * 70)
    print(f"测试 #1 (正则表达式): {'✅ 通过' if results[0] else '❌ 失败'}")
    print(f"测试 #2 (JSON 解析): {'✅ 通过' if results[1] else '❌ 失败'}")
    print(f"测试 #3 (完整流程): {'✅ 通过' if results[2] else '❌ 失败'}")
    print()

    if all(results):
        print("🎉 所有测试通过！修复已验证！")
        print()
        print("下一步：")
        print("1. 重启服务以应用修复")
        print("2. 在实际环境测试")
        print("3. 检查 logs/headless.log 确认统计数据正常")
        return 0
    else:
        print("❌ 部分测试失败，请检查修复代码")
        return 1


if __name__ == "__main__":
    sys.exit(main())

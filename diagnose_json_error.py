#!/usr/bin/env python3
"""
诊断 "Extra data: line 1 column 460" JSON 解析错误
"""

import re

# 从日志中提取错误相关的信息
def analyze_error():
    print("=" * 80)
    print("诊断报告：JSON 解析错误 'Extra data: line 1 column 460'")
    print("=" * 80)

    print("\n## 1. 错误症状分析\n")
    print("❌ 错误信息: Extra data: line 1 column 460 (char 459)")
    print("📍 发生位置: stream/proxy_server.py:303-311")
    print("🔍 错误类型: json.JSONDecodeError")
    print("\n这个错误通常意味着：")
    print("  1. JSON 字符串在第 460 个字符后还有额外的数据")
    print("  2. 可能是多个 JSON 对象连在一起（没有适当的分隔）")
    print("  3. 可能是响应数据包含了多个 chunk，每个 chunk 是一个完整的 JSON")

    print("\n## 2. 问题根源分析\n")
    print("根据日志，问题发生在：")
    print("  - 时间: 17:35:41 到 17:35:49 之间")
    print("  - 连续出现 9 次相同错误")
    print("  - 发生在 Gemini API 流式响应处理过程中")
    print("\n可能的原因：")
    print("  ✓ Gemini API 的 GenerateContent 响应格式可能包含多个 JSON 块")
    print("  ✓ 当前的 process_response 尝试一次性解析整个 body_data")
    print("  ✓ 但 body_data 可能包含: {json1}{json2}{json3}... 这样的格式")

    print("\n## 3. 相关代码位置\n")
    print("stream/proxy_server.py:303-308")
    print("""```python
resp = await self.interceptor.process_response(
    body_data, host, "", headers
)
if self.queue is not None:
    self.queue.put(json.dumps(resp))
```""")

    print("\nstream/interceptors.py:87-108")
    print("  - parse_response() 方法使用正则表达式匹配 JSON")
    print("  - pattern = rb'\\[\\[\\[null,.*?],\"model\"]]'")
    print("  - 这个正则能匹配多个 JSON 块")

    print("\n## 4. 影响评估\n")
    print("从日志看：")
    print("  ⚠️ 虽然有 9 次 JSON 解析错误")
    print("  ✅ 但流式响应最终完成了（已收到:1项）")
    print("  ✅ completion_tokens: 4, prompt_tokens: 713")
    print("  ⚠️ 但只收到了 1 项数据，可能丢失了部分响应内容")
    print("\n结论：错误没有导致完全失败，但可能导致响应不完整")

    print("\n## 5. 需要的额外信息\n")
    print("为了更好地诊断问题，需要：")
    print("\n1. 📋 原始响应数据样本")
    print("   - 在 proxy_server.py:303 之前添加日志")
    print("   - 打印 body_data 的前 1000 个字符")
    print("   - 这样可以看到实际的响应格式")
    print("\n2. 🔍 拦截器的详细日志")
    print("   - stream/interceptors.py 中的 parse_response")
    print("   - 查看正则匹配了多少个 JSON 块")
    print("   - 查看每个块的内容")
    print("\n3. 📊 完整的请求-响应流程")
    print("   - 从 VSCode 发送请求开始")
    print("   - 到最终响应结束")
    print("   - 包括所有中间状态")

    print("\n## 6. 建议的调试步骤\n")
    print("\n### 步骤 1: 添加原始数据日志")
    print("""在 stream/proxy_server.py:302 添加：
```python
if should_sniff:
    self.logger.debug(f"原始 body_data 长度: {len(body_data)}")
    self.logger.debug(f"原始 body_data 前 1000 字符: {body_data[:1000]}")
    try:
        resp = await self.interceptor.process_response(...)
```""")

    print("\n### 步骤 2: 添加拦截器详细日志")
    print("""在 stream/interceptors.py:87-92 添加：
```python
def parse_response(self, response_data):
    pattern = rb'\\[\\[\\[null,.*?],\"model\"]]'
    matches = []
    for match_obj in re.finditer(pattern, response_data):
        matches.append(match_obj.group(0))

    self.logger.debug(f"找到 {len(matches)} 个 JSON 块")
    for i, match in enumerate(matches):
        self.logger.debug(f"JSON 块 {i+1}: {match[:200]}")
```""")

    print("\n### 步骤 3: 重现并收集数据")
    print("  1. 重启服务")
    print("  2. 在 VSCode 中触发一次请求")
    print("  3. 查看新的日志输出")
    print("  4. 提供完整的日志片段")

    print("\n## 7. 可能的解决方案\n")
    print("\n### 方案 A: 忽略 JSON 解析错误（临时）")
    print("  - 已经在代码中实现了 try-except")
    print("  - 错误被捕获，不会导致崩溃")
    print("  - 但可能丢失部分响应数据")

    print("\n### 方案 B: 修复 JSON 解析逻辑")
    print("  - 在 parse_response 中正确处理多个 JSON 块")
    print("  - 可能需要修改解析逻辑")
    print("  - 确保所有块都被正确提取")

    print("\n### 方案 C: 在 proxy_server 层面分割 JSON")
    print("  - 在调用 interceptor 之前")
    print("  - 先将 body_data 分割成独立的 JSON 块")
    print("  - 逐个传递给 interceptor")

    print("\n" + "=" * 80)
    print("✅ 诊断完成")
    print("=" * 80)
    print("\n下一步：请提供上述「需要的额外信息」中的任何一项，以便进一步分析")


if __name__ == "__main__":
    analyze_error()

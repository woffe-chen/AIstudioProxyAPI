#!/usr/bin/env python3
"""
Gemini 原始响应完整分析工具

从 debug_output/gemini_raw_chunks.jsonl 读取完整的原始数据并进行深度分析
"""

import json
from pathlib import Path
from datetime import datetime


def analyze_raw_chunks():
    print("=" * 80)
    print("🔍 Gemini 原始响应完整分析")
    print("=" * 80)
    print()

    chunks_file = Path('debug_output/gemini_raw_chunks.jsonl')

    if not chunks_file.exists():
        print(f"❌ 文件不存在: {chunks_file}")
        print()
        print("请确认：")
        print("  1. 服务已启动并修改了 interceptors.py")
        print("  2. 至少触发过一次请求")
        print()
        return

    # 读取所有 chunk
    chunks = []
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    chunk = json.loads(line)
                    chunks.append(chunk)
                except Exception as e:
                    print(f"⚠️  解析行失败: {e}")

    if not chunks:
        print("⚠️  未找到任何 chunk 数据")
        return

    print(f"✅ 找到 {len(chunks)} 个原始响应 chunk")
    print()

    # 创建详细分析文件
    output_dir = Path('debug_output')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'gemini_complete_analysis_{timestamp}.txt'

    total_bytes = 0
    total_content_chars = 0
    all_contents = []

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Gemini API 原始响应完整分析\n")
        f.write(f"分析时间: {datetime.now()}\n")
        f.write(f"总 Chunk 数: {len(chunks)}\n")
        f.write("=" * 80 + "\n\n")

        for chunk in chunks:
            chunk_num = chunk['chunk_num']
            data_hex = chunk['data_hex']
            length = chunk['length']

            total_bytes += length

            f.write(f"--- Chunk {chunk_num} ---\n")
            f.write(f"字节长度: {length}\n")

            # 从 hex 恢复字节
            try:
                chunk_bytes = bytes.fromhex(data_hex)
                chunk_str = chunk_bytes.decode('utf-8')

                f.write(f"解码成功: {len(chunk_str)} 字符\n")

                # 尝试解析 JSON
                try:
                    data = json.loads(chunk_str, strict=False)
                    f.write("✅ JSON 解析成功\n")

                    # 递归提取所有内容
                    def extract_content(obj):
                        contents = []
                        if isinstance(obj, list):
                            for item in obj:
                                # 检查 [[...], "model"] 模式
                                if isinstance(item, list) and len(item) >= 2 and item[1] == "model":
                                    payload_list = item[0]
                                    for payload in payload_list:
                                        if isinstance(payload, list) and len(payload) >= 2:
                                            content = payload[1]
                                            if content and isinstance(content, str):
                                                contents.append(content)
                                # 递归
                                contents.extend(extract_content(item))
                        return contents

                    contents = extract_content(data)

                    if contents:
                        f.write(f"提取到 {len(contents)} 个内容块:\n")
                        for idx, content in enumerate(contents):
                            f.write(f"\n  内容块 {idx+1}:\n")
                            f.write(f"  长度: {len(content)} 字符\n")
                            f.write(f"  预览: {content[:100]}...\n")

                            total_content_chars += len(content)
                            all_contents.append(content)
                    else:
                        f.write("⚠️  未提取到内容\n")

                except json.JSONDecodeError as e:
                    f.write(f"❌ JSON 解析失败: {e}\n")
                    f.write(f"原始数据前 200 字符: {chunk_str[:200]}\n")

            except Exception as e:
                f.write(f"❌ 处理失败: {e}\n")

            f.write("\n")

        # 写入总结
        f.write("=" * 80 + "\n")
        f.write("📊 分析总结\n")
        f.write("=" * 80 + "\n")
        f.write(f"总 Chunk 数: {len(chunks)}\n")
        f.write(f"总字节数: {total_bytes}\n")
        f.write(f"总内容字符数: {total_content_chars}\n")
        f.write(f"提取的内容块数: {len(all_contents)}\n")

    print(f"✅ 详细分析已保存到: {output_file}")
    print()

    # 控制台显示摘要
    print("📊 数据摘要:")
    print("-" * 80)
    for idx, content in enumerate(all_contents):
        print(f"  内容块 {idx+1}: {len(content)} 字符")
        print(f"    {content[:80]}...")
    print("-" * 80)
    print(f"📈 总计: {len(chunks)} 个 chunk, {total_bytes} 字节, {total_content_chars} 字符内容")
    print()


if __name__ == '__main__':
    print()
    print("🚀 启动 Gemini 原始响应完整分析工具")
    print()

    analyze_raw_chunks()

    print()
    print("=" * 80)
    print("✅ 分析完成")
    print("=" * 80)
    print()

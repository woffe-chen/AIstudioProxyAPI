#!/usr/bin/env python3
"""
Gemini 原始响应捕获工具

功能：
1. 捕获 Gemini API 返回的原始字节流
2. 解析并保存完整的响应数据
3. 对比处理前后的数据差异

使用方法：
1. 在 stream/interceptors.py 的 parse_response 方法开始处添加日志记录
2. 运行服务并触发一次请求
3. 运行此脚本分析日志：python3 capture_gemini_raw_response.py
"""

import json
import re
from pathlib import Path
from datetime import datetime


def extract_raw_responses_from_log(log_file=None):
    """从日志文件中提取原始响应数据"""

    print("=" * 80)
    print("🔍 Gemini 原始响应捕获分析")
    print("=" * 80)
    print()

    # 尝试多个可能的日志文件
    if log_file is None:
        log_files = [
            'logs/proxy_server.log',
            'logs/headless.log',
            'logs/app.log',
        ]
        for f in log_files:
            if Path(f).exists():
                log_file = f
                print(f"✅ 使用日志文件: {log_file}")
                print()
                break

    if not Path(log_file).exists():
        print(f"❌ 日志文件不存在: {log_file}")
        return

    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    # 查找原始响应数据的日志
    # 格式: [RAW_RESPONSE] chunk_X: b'...'
    # 修复：匹配到行尾，处理数据中的转义引号
    raw_pattern = r'\[RAW_RESPONSE\] chunk_(\d+): (b\'.+?)$'

    chunks = []
    for match in re.finditer(raw_pattern, log_content, re.MULTILINE):
        chunk_num = int(match.group(1))
        chunk_data = match.group(2)
        chunks.append((chunk_num, chunk_data))

    if not chunks:
        print("⚠️  未找到 [RAW_RESPONSE] 标记的日志")
        print()
        print("请在 stream/interceptors.py 的 parse_response() 方法开始处添加：")
        print()
        print("  self.logger.info(f'[RAW_RESPONSE] chunk_{self._parse_call_count}: {response_data}')")
        print()
        return

    print(f"✅ 找到 {len(chunks)} 个原始响应 chunk")
    print()

    # 保存到文件
    output_dir = Path('debug_output')
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'gemini_raw_response_{timestamp}.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Gemini API 原始响应数据\n")
        f.write(f"捕获时间: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for chunk_num, chunk_data in chunks:
            f.write(f"--- Chunk {chunk_num} ---\n")
            f.write(f"原始数据: {chunk_data}\n")

            # 尝试解析
            try:
                # 移除 b' 前缀和 ' 后缀
                if chunk_data.startswith("b'") and chunk_data.endswith("'"):
                    chunk_bytes = eval(chunk_data)  # 安全：这是从日志中读取的

                    f.write(f"字节长度: {len(chunk_bytes)}\n")

                    # 尝试解析 JSON
                    # 修复：匹配完整的 JSON 块结构
                    # 格式：[[[[[[null,"content"]],"model"]]],...]
                    pattern = rb'\[\[\[null,"[^"]*(?:\\.[^"]*)*"(?:\]|,).*?\],"model"\]\]'
                    matches = re.findall(pattern, chunk_bytes, re.DOTALL)

                    if matches:
                        f.write(f"JSON 块数量: {len(matches)}\n")
                        for i, match in enumerate(matches):
                            f.write(f"\n  JSON 块 {i+1}:\n")
                            f.write(f"  原始: {match}\n")

                            try:
                                json_data = json.loads(match, strict=False)
                                payload = json_data[0][0]
                                if payload and len(payload) > 1:
                                    content = payload[1]
                                    f.write(f"  提取内容: {repr(content)}\n")
                                    f.write(f"  内容长度: {len(content)} 字符\n")
                            except Exception as e:
                                f.write(f"  ❌ 解析失败: {e}\n")
                    else:
                        f.write("⚠️  未匹配到 JSON 块\n")
                        f.write(f"原始字节前 200 字符: {chunk_bytes[:200]}\n")

            except Exception as e:
                f.write(f"❌ chunk 解析错误: {e}\n")

            f.write("\n")

    print(f"✅ 详细分析已保存到: {output_file}")
    print()

    # 在控制台显示摘要
    print("📊 数据摘要:")
    print("-" * 80)

    total_bytes = 0
    total_content_chars = 0

    for chunk_num, chunk_data in chunks:
        try:
            if chunk_data.startswith("b'") and chunk_data.endswith("'"):
                chunk_bytes = eval(chunk_data)
                total_bytes += len(chunk_bytes)

                # 提取内容
                pattern = rb'\[\[\[null,.*?],"model"]]'
                matches = re.findall(pattern, chunk_bytes)

                for match in matches:
                    try:
                        json_data = json.loads(match, strict=False)
                        payload = json_data[0][0]
                        if payload and len(payload) > 1:
                            content = payload[1]
                            total_content_chars += len(content)
                            print(f"  Chunk {chunk_num}: {len(content)} 字符 | {repr(content[:50])}...")
                    except:
                        pass
        except:
            pass

    print("-" * 80)
    print(f"📈 总计: {len(chunks)} 个 chunk, {total_bytes} 字节, {total_content_chars} 字符内容")
    print()


def analyze_interceptor_processing():
    """分析拦截器处理前后的数据对比"""

    print("=" * 80)
    print("🔬 拦截器处理分析")
    print("=" * 80)
    print()

    # 尝试多个可能的日志文件
    log_files = [
        'logs/proxy_server.log',
        'logs/app.log',
        'logs/headless.log',
    ]
    log_file = None
    for f in log_files:
        if Path(f).exists():
            log_file = f
            break

    if not log_file or not Path(log_file).exists():
        print(f"❌ 日志文件不存在")
        return

    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    # 查找统计信息
    stats_pattern = r'\[统计\] 调用: (\d+) 次, 提取: (\d+) 字节, 发送: (\d+) 字节, 缓冲区: (\d+) 字节'
    final_pattern = r'\[最终统计\] 总调用: (\d+), 总提取: (\d+) 字节, 总发送: (\d+) 字节, 丢失: (-?\d+) 字节 \(([\d.]+)%\)'

    stats_matches = list(re.finditer(stats_pattern, log_content))
    final_matches = list(re.finditer(final_pattern, log_content))

    if not stats_matches and not final_matches:
        print("⚠️  未找到统计信息")
        print("请确认 interceptors.py 中已启用统计模式")
        return

    if stats_matches:
        print(f"✅ 找到 {len(stats_matches)} 条中间统计")
        print()
        print("📊 处理进度:")
        for match in stats_matches[-5:]:  # 显示最后 5 条
            calls, extracted, sent, buffered = match.groups()
            print(f"  调用 {calls} 次: 提取 {extracted}B, 发送 {sent}B, 缓冲 {buffered}B")
        print()

    if final_matches:
        print("📈 最终统计:")
        for match in final_matches[-3:]:  # 显示最后 3 次请求
            calls, extracted, sent, lost, percent = match.groups()
            print(f"  总调用: {calls}, 提取: {extracted}B, 发送: {sent}B, 丢失: {lost}B ({percent}%)")
        print()

        # 分析最后一次
        last_match = final_matches[-1]
        calls, extracted, sent, lost, percent = last_match.groups()

        extracted_int = int(extracted)
        sent_int = int(sent)
        lost_int = int(lost)
        percent_float = float(percent)

        print("🔍 最后一次请求分析:")
        if extracted_int == 0:
            print("  ❌ 从 Gemini API 提取的数据为 0 字节")
            print("  → 可能原因: 正则表达式不匹配 / JSON 解析全部失败")
        elif sent_int == 0:
            print("  ❌ 发送给客户端的数据为 0 字节")
            print("  → 可能原因: 缓冲逻辑阻塞了所有数据")
        elif percent_float > 50:
            print(f"  ⚠️  数据丢失率高达 {percent}%")
            print("  → 可能原因: 缓冲窗口逻辑过度缓冲")
        elif percent_float < 10:
            print(f"  ✅ 数据丢失率较低 ({percent}%)")
            print("  → 可能是正常的工具调用 JSON 块被隐藏")
        else:
            print(f"  ⚠️  数据丢失率: {percent}%")
            print("  → 需要进一步调查")


if __name__ == '__main__':
    print()
    print("🚀 启动 Gemini 原始响应分析工具")
    print()

    # 步骤 1: 提取原始响应
    extract_raw_responses_from_log()

    # 步骤 2: 分析处理流程
    analyze_interceptor_processing()

    print()
    print("=" * 80)
    print("✅ 分析完成")
    print("=" * 80)
    print()
    print("📝 下一步:")
    print("  1. 查看 debug_output/ 目录下的详细分析文件")
    print("  2. 对比原始数据和最终统计，找出数据丢失的环节")
    print("  3. 根据分析结果调整 interceptors.py 中的处理逻辑")
    print()

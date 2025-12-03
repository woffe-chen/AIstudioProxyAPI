#!/usr/bin/env python3
"""
快速测试脚本：验证原始数据捕获是否正常工作

使用方法：
1. 重启服务
2. 触发一次请求
3. 运行此脚本检查日志
"""

import re
from pathlib import Path


def quick_test():
    print("🧪 快速测试：检查原始数据捕获是否正常")
    print("=" * 80)
    print()

    # 尝试多个可能的日志文件
    log_files = [
        Path('logs/proxy_server.log'),
        Path('logs/app.log'),
        Path('logs/headless.log'),
    ]

    log_file = None
    for f in log_files:
        if f.exists():
            log_file = f
            print(f"✅ 找到日志文件: {log_file}")
            print()
            break

    if not log_file:
        print("❌ 未找到日志文件")
        print()
        print("请确认：")
        print("  1. 服务已启动")
        print("  2. 至少触发过一次请求")
        print()
        return False

    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    # 检查是否有 [RAW_RESPONSE] 标记
    raw_response_pattern = r'\[RAW_RESPONSE\] chunk_\d+:'
    matches = re.findall(raw_response_pattern, log_content)

    if matches:
        print(f"✅ 找到 {len(matches)} 条原始响应日志")
        print()
        print("示例：")
        # 显示前 3 条
        for match in re.finditer(raw_response_pattern + r'.*', log_content)[:3]:
            line = match.group(0)
            print(f"  {line[:100]}...")
        print()
        print("✅ 原始数据捕获正常工作！")
        print()
        print("下一步：运行完整分析")
        print("  python3 capture_gemini_raw_response.py")
        print()
        return True
    else:
        print("⚠️  未找到 [RAW_RESPONSE] 日志")
        print()
        print("可能的原因：")
        print("  1. 服务未重启（修改代码后需要重启）")
        print("  2. 没有触发过请求")
        print("  3. 日志级别过滤掉了 INFO 级别")
        print()
        print("解决方法：")
        print("  1. 停止服务：pkill -f 'python.*main.py'")
        print("  2. 启动服务：poetry run python main.py --headless")
        print("  3. 在 VSCode 中触发一次请求")
        print("  4. 重新运行此脚本")
        print()
        return False


if __name__ == '__main__':
    quick_test()

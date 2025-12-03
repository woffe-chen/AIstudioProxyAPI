# 流式缓冲调试脚本说明

本目录包含多个调试脚本,用于验证和诊断第三版流式缓冲机制。所有脚本基于 [claude.md](claude.md) 文档中的实现方案。

## 快速索引

| 脚本 | 用途 | 使用场景 |
|------|------|---------|
| [debug_stream_buffering.py](#debug_stream_bufferingpy) | 综合测试 | 验证所有核心功能 |
| [debug_statistics_mode.py](#debug_statistics_modepy) | 统计模式 | 检测数据丢失率 |
| [debug_aggressive_buffering.py](#debug_aggressive_bufferingpy) | 问题诊断 | 诊断缓冲窗口问题 |

---

## debug_stream_buffering.py

### 功能
综合测试第三版流式缓冲机制的所有核心功能。

### 测试场景

1. **跨 chunk 标记检测**
   - 模拟 ` ```json ` 标记被分割到多个 chunk
   - 验证能否正确检测并进入缓冲模式
   - 验证 JSON 块是否被成功隐藏

2. **周期性保活机制**
   - 模拟 2 秒缓冲期间
   - 验证每 0.5 秒发送一次保活消息
   - 检查保活间隔是否正确

3. **超时保护**
   - 模拟缓冲超过 2.5 秒
   - 验证强制释放机制
   - 验证状态是否正确重置

4. **缓冲窗口优化**
   - 测试普通文本立即发送
   - 测试 Python 代码块不触发过度缓冲
   - 测试包含 tool_call 关键字的处理
   - 测试以 ` ``` ` 结尾的处理

5. **统计模式验证**（可选）
   - 需要先实施方案 C
   - 验证数据提取和发送的统计

### 使用方法

```bash
# 运行所有测试
poetry run python debug_stream_buffering.py

# 或直接运行（如果已激活虚拟环境）
python3 debug_stream_buffering.py
```

### 预期输出

```
======================================================================
测试场景 1: 跨 chunk 标记检测
======================================================================

开始模拟流式响应 (共 6 个 chunk)
...

【验证结果】
✅ 成功提取函数调用
✅ JSON 块已成功隐藏
✅ 前置和后续内容正确发送

...

🎉 所有测试场景执行完成
```

---

## debug_statistics_mode.py

### 功能
验证统计模式（方案 C）的实施情况,追踪数据提取和发送的字节数。

### 使用场景

当怀疑数据被卡在缓冲区时使用此脚本:
- completion_tokens 异常低（<10）
- 响应内容几乎为空
- "有内容: False" 的情况

### 使用方法

```bash
# 检查统计模式是否已实施
poetry run python debug_statistics_mode.py
```

### 预期输出

**未实施时:**
```
❌ 统计模式尚未实施

需要在 stream/interceptors.py 的 HttpInterceptor 类中添加:
...
```

**已实施时:**
```
✅ 统计模式已实施

模拟数据流测试
...

[最终统计] 总调用: 7, 总提取: 150 字节, 总发送: 140 字节, 丢失: 10 字节 (6.7%)

【判断标准】
- 数据丢失率 <10%  → ✅ 正常
- 数据丢失率 10-50% → ⚠️  需要检查
- 数据丢失率 >50%  → ❌ 严重问题
```

---

## debug_aggressive_buffering.py

### 功能
专门诊断激进缓冲窗口修复后的问题（claude.md lines 1446-1650）。

### 问题背景

18:40 实施激进缓冲窗口修复后,数据丢失问题依然存在:
- completion_tokens 只有 4
- 响应几乎完全为空
- "有内容: False, 收到项目数: 1"

### 测试场景

1. **短 chunk 阻塞问题**
   - 测试包含 `tool_call` 关键字的短 chunk（≤10 字节）
   - 测试以 ` ``` ` 结尾的短 chunk
   - 验证是否被阻塞在缓冲区

2. **连续短 chunk 持续无输出**
   - 模拟 10 个连续的短 chunk
   - 统计数据丢失率
   - 验证是否导致持续无输出

3. **普通代码块误判**
   - 测试包含 ` ```python ` 的响应
   - 验证激进方案是否避免了误判

### 使用方法

```bash
poetry run python debug_aggressive_buffering.py
```

### 预期输出

```
======================================================================
激进缓冲窗口问题诊断
======================================================================

--- 测试: 激进缓冲窗口问题重现 ---
...
❌ 确认问题: 数据被阻塞在缓冲区

--- 测试: 连续短 chunk 导致持续无输出 ---
...
数据丢失: 45 字节 (75.0%)
❌ 严重问题: 超过 50% 的数据被阻塞

--- 修复建议 ---
...
```

---

## 其他调试脚本（历史）

以下脚本是开发过程中创建的,主要用于理解问题根源:

| 脚本 | 用途 |
|------|------|
| test_buffering.py | 第一版测试（已过时） |
| test_buffering_simple.py | 简化测试（第二版） |
| test_buffering_v3.py | 第三版测试（官方） |
| debug_buffering.py | 逐步调试缓冲逻辑 |
| debug_json_format.py | JSON 格式和正则匹配 |
| debug_regex.py | 正则表达式验证 |
| debug_regex2.py | 正则模式对比 |
| debug_payload.py | Gemini 响应数据结构 |
| diagnose_json_error.py | JSON 解析错误诊断 |
| test_json_fix.py | JSON 修复验证 |

---

## 实施优先级

根据 claude.md 的三层调试策略:

### 优先级 1: 统计模式（轻量级）

**目标**: 快速确认数据是否卡在缓冲区

**步骤**:
1. 在 `HttpInterceptor.__init__` 中添加统计计数器
2. 在 `parse_response` 中记录提取和发送的字节数
3. 在 `_reset_buffer_state` 中输出最终统计
4. 运行 `debug_statistics_mode.py` 验证

**判断依据**:
- 数据丢失率 >50% → 进入优先级 2
- 数据丢失率 <10% → 检查上游（proxy_server.py）
- 数据丢失率 10-50% → 同时检查拦截器和上游

### 优先级 2: 详细 Chunk 追踪

**目标**: 追踪每个 chunk 的处理细节

**步骤**:
1. 在 `parse_response` 中添加详细日志
2. 运行实际 Gemini API 请求
3. 分析日志,找出数据被阻塞的具体位置

### 优先级 3: 上游数据检查

**目标**: 确认 Gemini API 是否返回了完整数据

**步骤**:
1. 在 `proxy_server.py` 中记录原始数据大小
2. 对比 Gemini API 返回 vs 拦截器提取 vs 最终发送
3. 确定数据丢失发生在哪一层

---

## 相关文档

- [claude.md](claude.md) - 完整的实现文档和问题诊断记录
- [stream/summary.md](stream/summary.md) - 流式处理架构总结
- [stream/interceptors.py](stream/interceptors.py) - 核心实现文件

---

## 常见问题

### Q: 为什么需要这么多调试脚本?

A: 流式缓冲机制涉及多个层次的交互:
- Gemini API 响应 → proxy_server.py → interceptors.py → response_generators.py → 客户端
- 每个环节都可能导致问题,需要分层诊断

### Q: 哪个脚本最重要?

A: **debug_statistics_mode.py** 最重要,它能快速定位数据是否卡在缓冲区。

### Q: 测试失败怎么办?

A: 按照以下顺序排查:
1. 检查 `stream/interceptors.py` 是否是第三版实现
2. 运行 `debug_stream_buffering.py` 验证核心功能
3. 如果怀疑数据丢失,运行 `debug_statistics_mode.py`
4. 如果怀疑缓冲窗口问题,运行 `debug_aggressive_buffering.py`

---

**最后更新**: 2025-12-02
**对应版本**: 第三版流式缓冲机制 + 激进缓冲窗口修复
**状态**: 开发完成,待验证

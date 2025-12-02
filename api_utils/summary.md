# api_utils Summary

- Hosts the FastAPI application logic: `app.py` wires lifespan startup (logging, stream proxy, Playwright init) and exposes the `create_app()` used by `server.py`.
- `request_processor.py`, `queue_worker.py`, `response_generators.py`, and `response_payloads.py` contain the core `/v1/chat/completions` flow—validating OpenAI-style payloads, handling tool calls, coordinating with `browser_utils` for model switching, and streaming SSE chunks.
- **工具调用（Tool Calling）支持**：
  - `utils.py` 的 `prepare_combined_prompt()` 在提示中注入工具协议说明和可用工具目录，引导 Gemini 模型以 JSON 格式输出工具调用指令
  - `tools_registry.py` 管理工具注册（`register_runtime_tools()`）和执行（`execute_tool_call()`），支持运行时动态注册 MCP 工具
  - `sse.py` 提供生成 OpenAI 格式的工具调用 SSE 事件（`generate_sse_tool_call_chunk()`），确保客户端兼容性
  - `response_generators.py` 协调工具调用的完整流程：解析模型输出 → 执行工具 → 追加工具结果消息 → 继续对话
- Authentication helpers (`auth_utils.py`, `dependencies.py`, `client_connection.py`) manage API key files under `auth_profiles/` and monitor websocket disconnects.
- `routers/` offers modular FastAPI routes (health, models list, chat, static assets, log websocket, queue status) so the main app stays thin.
- Utility modules (`common_utils.py`, `context_init.py`, `context_types.py`, `utils.py`, `utils_ext/`) provide shared helpers for prompt assembly, token estimation, error shaping, and runtime configuration.

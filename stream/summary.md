# stream Summary

- Implements the standalone HTTPS MITM proxy that forms the first layer of the "three-tier" response pipeline.
- `main.py` exposes both a CLI and an embeddable `builtin()` entry point used by FastAPI to spawn the proxy in a separate process.
- `proxy_server.py`, `proxy_connector.py`, and `interceptors.py` handle socket tunneling, domain filtering (`*.google.com`), request/response rewrites, and queue-based streaming back to FastAPI.
- **伪函数调用拦截器（Pseudo-Function Calling Interceptor）**：
  - `interceptors.py` 的 `HttpInterceptor` 拦截并解析模型响应中的工具调用指令
  - 通过正则表达式匹配 JSON 格式的工具调用块（````json {"tool_call": {...}} ```）
  - 将解析出的工具调用转换为内部 `function` 格式，并从响应正文中移除原始 JSON 块，避免在客户端显示
  - 支持提取函数名（`name`）和参数（`arguments`），确保与 OpenAI Function Calling 协议兼容
- `cert_manager.py` and `utils.py` manage certificate loading, caching, and helper routines for parsing requests.

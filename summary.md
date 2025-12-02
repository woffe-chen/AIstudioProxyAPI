# AIstudioProxyAPI 项目摘要

## 定位与目标
- 将 Google AI Studio 网页交互转换为兼容 OpenAI `/v1/chat/completions` 的 API，允许现有 OpenAI 客户端与第三方工具直接接入。
- 通过 Camoufox 反指纹浏览器 + Playwright 自动化保证登录/Gemini 模型调用的稳定性，并提供 `.env` 驱动的统一配置体验。

## 主要能力
- **三层响应链路**：首选本地 stream 代理 (`stream/`)，可选 Helper 服务，最后回退到 Playwright 页面操作，兼顾低延迟与功能完整度。
- **模型与参数管控**：`browser_utils/page_controller.py` 自动切换 AI Studio 模型，精细设置 `temperature/top_p/max_output_tokens/stop/reasoning_effort`，并支持 URL Context、Google Search、Thinking 模式等增强选项。
- **Gemini 工具调用（Tool Calling）**：
  - 通过提示工程和响应解析实现 OpenAI 风格的函数调用（Function Calling）能力
  - `stream/interceptors.py` 拦截并解析模型输出的 JSON 格式工具调用指令（`{"tool_call": {...}}`），并通过流式缓冲/超时机制将跨 chunk 的 ```json``` 代码块组装为完整的函数调用，避免原始 JSON 泄露到客户端
  - `api_utils/utils.py` 在提示中注入工具协议和可用工具目录，引导模型正确输出工具调用格式
  - `api_utils/tools_registry.py` 管理工具注册与执行，支持运行时动态注册 MCP 工具
  - 完全兼容 OpenAI 的 `tools` 和 `tool_choice` 参数
- **Thinking 模式与预算控制**：
  - `browser_utils/thinking_normalizer.py` 归一化 `reasoning_effort` 参数，支持多种输入格式（整数、字符串、预设值）
  - 支持 Gemini 2.0 Pro 的思考模式与预算限制（通过 token 数控制思考深度）
  - 可通过环境变量 `ENABLE_THINKING_BUDGET` 和 `DEFAULT_THINKING_BUDGET` 配置默认行为
  - 支持无头模式（headless）和有头模式下的思考预算切换
- **Web UI 与客户端兼容**：`webui.js` 提供内置聊天、日志、模型选择、API Key 管理，且 REST API 完全兼容 OpenAI SDK/Open WebUI 等客户端。
- **脚本注入与反检测**：脚本注入 v3.0 利用 Playwright 原生拦截挂载油猴脚本，Camoufox 则在底层伪装指纹，降低被识别的概率。
- **认证与密钥管理**：`auth_profiles/` 按 active/saved 区分认证文件，`api_utils/auth_utils.py` 管理 API Key，支持可选 Bearer token 校验。

## 运行与启动
- **CLI 启动**：`launch_camoufox.py` 负责 `.env` 载入、Camoufox/Playwright 进程、日志与 auth 目录初始化，可选 headed/headless/debug/virtual-display、stream/helper 端口等参数。
- **GUI 启动器**：`gui_launcher.py` (Tk) 封装有头/无头/虚拟显示启动、端口占用查询、代理配置和日志回放，便于桌面用户操作。
- **FastAPI 主应用**：`server.py` -> `api_utils/app.py` 负责加载配置、启动 stream 代理子进程、初始化 Playwright、注册 `/v1/*` 路由、日志 websocket 等。
- **脚本化运维**：`scripts/start.sh`/`scripts/stop.sh` 提供一键进程管理，启动脚本会在写入 PID 前自动使用 `lsof` 清理占用 `2048/3120/9222` 的遗留 Camoufox/stream 进程，若端口被第三方程序占用则直接提示手动处理，避免同一服务器多次部署后端口被卡住。

## 代码结构总览
- `api_utils/`：FastAPI 应用与业务逻辑（请求校验、SSE/WS、模型切换、工具执行、队列管理、路由与错误处理）。
- `browser_utils/`：对 AI Studio 页面的 Playwright 操作封装（初始化、操作、模型/参数缓存、脚本管理、错误快照等）。
- `stream/`：HTTPS 代理服务器及证书管理，用于低延迟流式转发与拦截。
- `config/`：常量、selectors、timeout、settings 统一导出，并提供 env helper。
- `docs/`：快速开始、环境变量、API 使用、Docker、脚本注入、开发指南等完整文档体系。

## 部署与依赖
- 推荐流程：`poetry install` → 复制 `.env.example` → `poetry run python launch_camoufox.py --debug` 完成首次认证 → `--headless` 日常运行。
- 关键依赖：FastAPI、Pydantic v2、Uvicorn、Playwright、Camoufox、aiohttp/requests、python-socks、dotenv。Poetry 管理运行/开发依赖，`pyproject.toml` 已列出。

## 关键优势
1. **OpenAI 兼容**：无需改造客户端即可复用现有生态。
2. **可靠性**：多级流式回退 + 反指纹浏览器，大幅减少页面失效概率。
3. **可观测性**：日志文件、Web UI 终端、健康检查、WS 日志订阅帮助运维排障。
4. **多平台覆盖**：macOS/Windows/Linux，Docker 与一键安装脚本均已提供。
5. **可扩展性**：模块化目录清晰，配置统一，易于定制脚本注入、模型过滤、工具链等。

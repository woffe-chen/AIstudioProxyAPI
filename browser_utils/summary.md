# browser_utils Summary

- Encapsulates all Playwright/Navigator automation against Google AI Studio.
- `page_controller.py` provides the high-level API for adjusting parameters (temperature, tokens, reasoning budget, URL context, Google Search toggles), uploading files, and reading responses safely.
- `initialization.py` bootstraps pages (temporary chat mode, UI readiness), while `model_management.py` and `operations.py` contain helpers for switching models, waiting for completions, and saving diagnostic snapshots.
- **Thinking 模式归一化**：
  - `thinking_normalizer.py` 将 `reasoning_effort` 参数归一化为标准化的 `ThinkingDirective` 指令
  - 支持多种输入格式：整数（token 数）、字符串（"low"/"medium"/"high"/"none"/"0"/"-1"）或 None（使用默认配置）
  - 提供三个核心字段：`thinking_enabled`（总开关）、`budget_enabled`（预算开关）、`budget_value`（具体 token 数）
  - 配合 `page_controller.py` 实现 Gemini 2.0 Pro 思考模式的精细控制，包括无头模式下的预算切换
- `script_manager.py` handles Tampermonkey-style script injection via native network interception, and `more_modles.js` bundles custom JavaScript the automation can inject when AI Studio's UI lacks required selectors.

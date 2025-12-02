# config Summary

- Provides a single import surface (`__init__.py`) that re-exports constants, selectors, settings, and timeout values for the rest of the codebase.
- `constants.py` defines defaults such as the fallback model name, stream timeout flags, and shared string markers used when stitching prompts.
- `selectors.py` centralizes all CSS selectors/DOM hooks Playwright relies on so UI changes can be handled in one file.
- `timeouts.py` lists polling intervals, click/response timeouts, and other timing knobs that control the automation cadence.
- `settings.py` reads environment variables (`.env` + OS env) and exposes helpers like `get_environment_variable`, ensuring configuration remains declarative and `.env`-driven.

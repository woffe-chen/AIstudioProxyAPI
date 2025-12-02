# models Summary

- Defines Pydantic schemas and structured helpers shared between API routes and browser automation.
- `chat.py` mirrors OpenAI-style chat payloads (messages, tool calls, attachments, reasoning parameters) and is reused by both FastAPI validation and Web UI serialization.
- `exceptions.py` introduces custom errors such as `ClientDisconnectedError` for clean cancellation handling.
- `logging.py` provides small logging-related dataclasses/utilities, while `__init__.py` re-exports the public models for convenience.

# logging_utils Summary

- Supplies shared logging configuration so both `server.py` and auxiliary launchers emit consistent, structured logs.
- `setup.py` defines `setup_server_logging()` and `restore_original_streams()` helpers used during FastAPI lifespan to attach file handlers, websocket broadcasters, and stdout redirection when needed.
- `__init__.py` exposes those helpers for simple imports across the codebase.

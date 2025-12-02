# auth_profiles Summary

- Central storage for Google AI Studio authentication artifacts and project API keys.
- `key.txt` is the default API key file consumed by `api_utils/auth_utils.py` when bearer-token enforcement is enabled.
- `active/` keeps the in-use Google credentials (cookies, tokens) that Camoufox/Playwright load at runtime, while `saved/` preserves backups to restore sessions quickly.
- These files are environment-specific secrets and are intentionally excluded from version control; ensure proper permissions when deploying.

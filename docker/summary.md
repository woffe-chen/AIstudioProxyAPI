# docker Summary

- Houses everything needed for containerized deployments.
- `Dockerfile` builds a multi-stage image with Poetry-managed dependencies and Playwright/Camoufox prerequisites; `docker-compose.yml` wires FastAPI, stream proxy, and volume mounts using the shared `.env` file.
- `README.md` and `README-Docker.md` provide quick-start vs. full deployment guides, while `SCRIPT_INJECTION_DOCKER.md` covers enabling the Tampermonkey injection pipeline inside containers.
- `update.sh` automates pulling the latest image and refreshing mounted assets for production hosts.

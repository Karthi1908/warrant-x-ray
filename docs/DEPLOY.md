# Warrant X-Ray Deployment Guide

This document specifies the deployment architecture and operations for running Warrant X-Ray on Linux containers and Nebius Serverless Endpoints.

## Target Platform: Linux Container on Nebius

### Container Topology
- Single multi-stage Linux container image running FastAPI and Uvicorn on port 8000.
- Serves both the compiled Vite + React Single-Page App from `web/dist` and the `/api/` REST and SSE endpoints.
- Runs with non-root security context.
- Health check path: `GET /api/health`.

### Always-On Instance Requirement
- The in-process collector scheduler and in-memory session service require **1 always-on replica** (minimum replicas = 1, maximum replicas = 1).
- Setting scale-to-zero would reset in-memory chat sessions and pause scheduled snapshot collection.

### Environment Configuration
All secrets and provider credentials MUST be provided as environment variables. Real secrets must NEVER be baked into container images or committed to version control.

| Variable | Description | Production Example |
|:---|:---|:---|
| `WX_NEBIUS_API_KEY` | Bearer key for Nebius Token Factory | `secret-token-...` |
| `WX_NEBIUS_BASE_URL` | Token Factory API Base | `https://api.tokenfactory.nebius.com/v1/` |
| `WX_TAVILY_API_KEY` | API Key for Tavily Search | `tvly-...` |
| `WX_SOURCE_ENABLED` | Master kill-switch for automated collector | `true` (or `false` if Gate B) |
| `WX_DB_URL` | SQLite database URI | `sqlite+aiosqlite:///data/warrantx.db` |
| `WX_ADMIN_TOKEN` | Bearer token to protect admin routes | `secure-random-admin-token` |
| `WX_SESSION_SECRET` | Salt for anonymous IP/UA hashing | `random-daily-salt-seed` |
| `WX_LOG_LEVEL` | Application logging level | `INFO` |

### Local Docker Run
```bash
docker compose up --build
```
Open http://localhost:8000 to access the application.

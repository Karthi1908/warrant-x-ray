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

---

## Spike T7 Verification: Deploy to Nebius

Spike T7 verified container deployment to Nebius Serverless Endpoints:
1. **Container Image**: Built using standard multi-stage `Dockerfile`:
   - Stage 1 (`node:20-slim`): Builds frontend via `npm run build` producing optimized static assets in `/app/web/dist` (<300 KB gzipped bundle).
   - Stage 2 (`python:3.11-slim`): Installs dependencies with `uv sync --frozen --no-dev`, copies frontend dist, and runs Uvicorn.
2. **Reverse Proxy Buffering**:
   - For SSE streaming (`/api/chat`), ensure proxy does not buffer chunks by serving `X-Accel-Buffering: no` and `Cache-Control: no-cache` (already set by FastAPI `StreamingResponse`).
3. **Storage & Persistence**:
   - Volume mount mapped at `/app/data` to persist SQLite snapshots (`warrantx.db`).
4. **Health Probe**:
   - Liveness & readiness probes configured to `GET /api/health` with initial delay 5s and timeout 3s.
5. **Cold Start & Always-on Policy**:
   - Replica configuration set to minimum 1 replica (`min_instances: 1`) to preserve in-memory sessions and prevent cold-start latency spikes.


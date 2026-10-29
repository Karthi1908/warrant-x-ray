# ==============================================================================
# Multi-stage Dockerfile for Warrant X-Ray
# Stage 1: Build the Vite + React Single-Page Application
# ==============================================================================
FROM node:20-alpine AS web-builder
WORKDIR /app/web

COPY web/package*.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Python Backend Runtime
# ==============================================================================
FROM python:3.11-slim AS runtime

# Install system utilities & curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy dependency specifications and install frozen environment
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev

# Copy application code and configurations
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Copy built frontend assets from web-builder stage
COPY --from=web-builder /app/web/dist ./web/dist

# Create data directory for SQLite persistence
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

ENV PORT=8000
ENV WX_MODE=live
ENV WX_SOURCE_ENABLED=true
ENV WX_TAVILY_RESEARCH=true
ENV WX_TAVILY_CRAWL=true
ENV WX_CHAT_ENABLED=true
EXPOSE 8000 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/health || exit 1

CMD ["sh", "-c", "uv run uvicorn warrantx.api.app:app --host 0.0.0.0 --port ${PORT}"]

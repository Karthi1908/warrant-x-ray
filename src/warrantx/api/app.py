"""FastAPI application factory and middleware configuration for Warrant X-Ray."""

from __future__ import annotations

import hashlib
import ipaddress
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from warrantx.api.errors import NotFoundError, register_error_handlers
from warrantx.api.logging import get_logger, request_id_ctx, setup_logging
from warrantx.api.routes.admin import router as admin_router
from warrantx.api.routes.chat import router as chat_router
from warrantx.api.routes.data import router as data_router
from warrantx.api.routes.meta import router as meta_router
from warrantx.api.routes.report import router as report_router
from warrantx.config import Settings, get_settings
from warrantx.data.repo import AsyncRepository, create_repo

logger = get_logger("warrantx.app")

# In-memory daily hash cache for unique visitor counting (reset daily)
_SEEN_DAILY_HASHES: set[str] = set()
_LAST_SEEN_DAY: str = ""
_SERVER_SALT: str = uuid.uuid4().hex


def _mask_ip_subnet(client_ip: str) -> str:
    """Extract masked subnet prefix from an IP address (/24 for IPv4, /48 for IPv6)."""
    try:
        ip = ipaddress.ip_address(client_ip)
        if ip.version == 4:
            # /24 subnet mask: zero last octet
            network = ipaddress.ip_network(f"{client_ip}/24", strict=False)
            return str(network.network_address)
        else:
            network = ipaddress.ip_network(f"{client_ip}/48", strict=False)
            return str(network.network_address)
    except Exception:
        return "0.0.0.0"


def _compute_daily_visitor_hash(client_ip: str, user_agent: str, day_str: str) -> str:
    """Compute one-way daily-salted cryptographic hash. Raw IP is never stored or logged."""
    subnet = _mask_ip_subnet(client_ip)
    payload = f"{subnet}|{user_agent}|{day_str}|{_SERVER_SALT}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management."""
    settings = get_settings()
    setup_logging(level=settings.log_level, json_format=settings.log_json)
    logger.info("warrantx_startup", mode=settings.mode, version="0.1.0")

    # Initialize persistence repository
    if not hasattr(app.state, "repo") or app.state.repo is None:
        repo = create_repo(settings.database_url)
        await repo.init_tables()
        app.state.repo = repo
    else:
        repo = app.state.repo
    app.state.mode = getattr(app.state, "mode", settings.mode)

    # Initialize news service
    tavily_gateway = None
    if settings.mode == "live" and settings.tavily_api_key:
        from warrantx.news.tavily_gateway import TavilyGateway
        tavily_gateway = TavilyGateway(
            api_key=settings.tavily_api_key,
            daily_credit_limit=settings.tavily_daily_credits,
        )
    from warrantx.news.cache import NewsService
    app.state.news_service = NewsService(
        repo=repo,
        mode=settings.mode,
        tavily_gateway=tavily_gateway,
    )

    # Auto-load synthetic sample database if empty (T081)
    try:
        latest = await repo.get_latest_good_snapshot()
        if latest is None:
            logger.info("loading_synthetic_sample_database")
            await repo.load_synthetic_sample_database()
    except Exception as e:
        logger.warning("sample_database_load_failed", error=str(e))

    yield

    logger.info("warrantx_shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the Warrant X-Ray FastAPI application."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Warrant X-Ray API",
        description="Chat-first risk copilot for Bursa Malaysia structured warrants",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Register standardized error handlers
    register_error_handlers(app)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Anonymous visitor session and daily usage tracking middleware
    @app.middleware("http")
    async def session_and_metrics_middleware(request: Request, call_next: Any) -> Response:
        global _SEEN_DAILY_HASHES, _LAST_SEEN_DAY

        # 1. Generate or pass-through request ID
        req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
        request_id_ctx.set(req_id)

        # 2. Ephemeral session UUID (X-Session-ID)
        session_id = request.headers.get("X-Session-ID") or request.cookies.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
        else:
            try:
                # Validate format
                uuid.UUID(session_id)
            except ValueError:
                session_id = str(uuid.uuid4())

        # 3. Privacy-preserving visitor tracking (for page and API hits)
        client_ip = request.client.host if request.client else "127.0.0.1"
        user_agent = request.headers.get("User-Agent", "unknown")
        today_my = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Daily hash rotation
        if today_my != _LAST_SEEN_DAY:
            _SEEN_DAILY_HASHES.clear()
            _LAST_SEEN_DAY = today_my

        visitor_hash = _compute_daily_visitor_hash(client_ip, user_agent, today_my)
        is_new_unique = visitor_hash not in _SEEN_DAILY_HASHES
        if is_new_unique:
            _SEEN_DAILY_HASHES.add(visitor_hash)

        repo: AsyncRepository | None = getattr(request.app.state, "repo", None)
        if repo and request.url.path.startswith("/api/"):
            try:
                await repo.record_visit(today_my, is_new_unique=is_new_unique)
            except Exception as e:
                logger.warning("metrics_record_failed", error=str(e))

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Session-ID"] = session_id
        return response

    # Health check endpoint
    @app.get("/api/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Container and cluster liveness probe."""
        return {
            "status": "ok",
            "mode": settings.mode,
            "version": "0.1.0",
        }

    # Register API routers
    app.include_router(meta_router)
    app.include_router(data_router)
    app.include_router(chat_router)
    app.include_router(report_router)
    if settings.admin_token:
        app.include_router(admin_router)

    # JSON 404 handler for any unmatched /api/* requests
    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        include_in_schema=False,
    )
    async def api_404_catchall(path: str) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "not_found",
                    "message": f"API endpoint '/api/{path}' not found",
                }
            },
        )

    # SPA static files serving and fallback
    dist_path = Path("web/dist")
    if dist_path.exists() and dist_path.is_dir():
        assets_path = dist_path / "assets"
        if assets_path.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> Response:
            file_path = dist_path / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            index_path = dist_path / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return JSONResponse(status_code=404, content={"message": "Frontend build not found"})

    return app


# Default app instance for ASGI servers (uvicorn warrantx.api.app:app)
app = create_app()

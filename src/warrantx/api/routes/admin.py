"""Admin routes guarded by bearer token (WX_ADMIN_TOKEN).

Implements FR-020, FR-023, and FR-CTRL-02:
- GET /api/admin/metrics: Operator metrics (token spend, tier breakdown, daily visits, unique visitors, queries, thresholds).
- POST /api/admin/cache/clear: Clears news and model caches.
- POST /api/admin/budget/reset: Resets today's daily LLM budget.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Header, Query, Request

from warrantx.api.budget import get_daily_budget_status
from warrantx.api.errors import UnauthorizedError
from warrantx.config import get_settings, load_flags
from warrantx.data.repo import AsyncRepository
from warrantx.llm.usage import get_malaysia_today

router = APIRouter(prefix="/api/admin", tags=["admin"])


def verify_admin_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """Validate Bearer admin token."""
    settings = getattr(request.app.state, "settings", None) or get_settings()
    if not settings.admin_token:
        raise UnauthorizedError("Admin endpoints are disabled on this instance")
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")
    token = authorization[7:].strip()
    if token != settings.admin_token:
        raise UnauthorizedError("Invalid admin token")


@router.get("/metrics", dependencies=[Depends(verify_admin_token)])
async def get_admin_metrics(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Retrieve detailed operator metrics: token spend, query breakdown, daily visits (FR-020, FR-023)."""
    repo: AsyncRepository = request.app.state.repo
    settings = getattr(request.app.state, "settings", None) or get_settings()
    flags = load_flags()

    # 1. Budget status
    budget_status = await get_daily_budget_status(repo)

    # 2. LLM Cost breakdown from llm_calls
    cost_data = await repo.get_cost_report_data(days=days)

    # 3. Usage metrics (visits, daily uniques, interactive query count)
    usage_records = await repo.list_usage_metrics(days=days)
    formatted_usage = [
        {
            "day": m.day,
            "visits": m.visit_count,
            "unique_visitors": m.unique_visitor_count,
            "interactive_queries": m.interactive_query_count,
        }
        for m in usage_records
    ]

    return {
        "status": "ok",
        "budget": budget_status,
        "llm_costs": cost_data,
        "usage_metrics": formatted_usage,
        "config": {
            "mode": settings.mode,
            "risk_free_rate": flags.get("risk_free_rate", 0.03),
            "flags": flags,
            "model_ultra": settings.model_ultra,
            "model_super": settings.model_super,
            "model_nano": settings.model_nano,
            "llm_daily_usd_cap": settings.llm_daily_usd_cap,
            "tavily_daily_credits": settings.tavily_daily_credits,
        },
    }


@router.post("/cache/clear", dependencies=[Depends(verify_admin_token)])
async def clear_cache(request: Request) -> dict[str, Any]:
    """Clear temporary news and model caches."""
    repo: AsyncRepository = request.app.state.repo
    deleted_count = await repo.clear_news_cache()

    # If news service has an in-memory cache, clear it
    news_service = getattr(request.app.state, "news_service", None)
    if news_service and hasattr(news_service, "clear_cache"):
        news_service.clear_cache()

    return {
        "status": "cleared",
        "deleted_entries": deleted_count,
    }


@router.post("/budget/reset", dependencies=[Depends(verify_admin_token)])
async def reset_budget(request: Request) -> dict[str, Any]:
    """Reset today's daily LLM budget counter."""
    repo: AsyncRepository = request.app.state.repo
    today = get_malaysia_today()
    await repo.reset_budget(day=today, kind="llm_usd")
    budget_status = await get_daily_budget_status(repo)
    return {
        "status": "reset",
        "budget": budget_status,
    }

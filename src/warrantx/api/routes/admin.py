"""Admin routes guarded by bearer token (WX_ADMIN_TOKEN).

Implements FR-020, FR-023, and FR-CTRL-02:
- GET /api/admin/metrics: Operator metrics (token spend, tier breakdown, daily visits, unique visitors, queries, Tavily crawl credits).
- POST /api/admin/collect: Trigger collector snapshot cycle with Tavily crawl or screener fallback.
- POST /api/admin/cache/clear: Clears news and model caches.
- POST /api/admin/budget/reset: Resets today's daily LLM and/or crawl budget.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel

from warrantx.api.budget import get_daily_budget_status
from warrantx.api.errors import UnauthorizedError
from warrantx.config import get_settings, load_flags
from warrantx.data.collector import Collector
from warrantx.data.repo import AsyncRepository
from warrantx.llm.usage import get_malaysia_today

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CollectRequest(BaseModel):
    """Optional payload specifying collection source."""

    source: str | None = None  # "tavily_crawl" | "direct_screener" | None


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
    """Retrieve detailed operator metrics: token spend, query breakdown, daily visits, Tavily crawl credits (FR-020, FR-023)."""
    repo: AsyncRepository = request.app.state.repo
    settings = getattr(request.app.state, "settings", None) or get_settings()
    flags = load_flags()
    today = get_malaysia_today()

    # 1. Budget status (LLM USD and Tavily crawl credits)
    budget_status = await get_daily_budget_status(repo)
    crawl_credits_used = await repo.get_budget_usage(day=today, kind="tavily_crawl_credits")
    crawl_credit_limit = getattr(settings, "tavily_crawl_credit_limit", 50)
    tavily_crawl_status = {
        "day": today,
        "used_credits": int(crawl_credits_used),
        "limit_credits": crawl_credit_limit,
        "remaining_credits": max(0, crawl_credit_limit - int(crawl_credits_used)),
        "is_exhausted": int(crawl_credits_used) >= crawl_credit_limit,
    }
    budget_status["tavily_crawl_credits"] = int(crawl_credits_used)
    budget_status["tavily_crawl_limit"] = crawl_credit_limit

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
        "tavily_crawl": tavily_crawl_status,
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
            "tavily_crawl": settings.tavily_crawl,
            "tavily_crawl_credit_limit": crawl_credit_limit,
        },
    }


@router.post("/collect", dependencies=[Depends(verify_admin_token)])
async def trigger_collection(
    request: Request,
    body: CollectRequest | None = None,
) -> dict[str, Any]:
    """Trigger a manual or on-demand warrant data collection cycle (T121, FR-020)."""
    repo: AsyncRepository = request.app.state.repo
    requested_source = body.source if body else None

    use_tavily = None
    if requested_source == "tavily_crawl":
        use_tavily = True
    elif requested_source == "direct_screener":
        use_tavily = False

    collector = Collector(
        repo=repo,
        use_tavily_crawl=use_tavily,
    )
    result = await collector.run_collection_cycle()
    return result


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
async def reset_budget(
    request: Request,
    kind: str = Query(default="all"),
) -> dict[str, Any]:
    """Reset today's daily LLM and/or crawl budget counter."""
    repo: AsyncRepository = request.app.state.repo
    today = get_malaysia_today()
    if kind in ("all", "llm_usd"):
        await repo.reset_budget(day=today, kind="llm_usd")
    if kind in ("all", "tavily_crawl_credits"):
        await repo.reset_budget(day=today, kind="tavily_crawl_credits")
    budget_status = await get_daily_budget_status(repo)
    return {
        "status": "reset",
        "budget": budget_status,
    }

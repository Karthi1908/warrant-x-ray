"""Daily spend cap and budget guardian.

Implements FR-CTRL-02:
- Checks consumed LLM and Tavily spend against daily ceilings.
- Provides daily budget status and spend tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from warrantx.config import get_settings
from warrantx.llm.usage import get_malaysia_today

if TYPE_CHECKING:
    from warrantx.data.repo import AsyncRepository


async def is_budget_exhausted(
    repo: AsyncRepository,
    limit_usd: float | None = None,
    day: str | None = None,
) -> bool:
    """Check if today's LLM compute spend has reached the configured threshold."""
    if limit_usd is None:
        settings = get_settings()
        limit_usd = getattr(settings, "llm_daily_usd_cap", 10.0)

    target_day = day or get_malaysia_today()
    used = await repo.get_budget_usage(day=target_day, kind="llm_usd")
    return used >= limit_usd


async def get_daily_budget_status(
    repo: AsyncRepository,
    limit_usd: float | None = None,
    day: str | None = None,
) -> dict[str, Any]:
    """Retrieve detailed status of daily LLM compute budget."""
    if limit_usd is None:
        settings = get_settings()
        limit_usd = getattr(settings, "llm_daily_usd_cap", 10.0)

    target_day = day or get_malaysia_today()
    used = await repo.get_budget_usage(day=target_day, kind="llm_usd")
    remaining = max(0.0, limit_usd - used)

    return {
        "day": target_day,
        "used_usd": round(used, 4),
        "limit_usd": round(limit_usd, 4),
        "remaining_usd": round(remaining, 4),
        "is_exhausted": used >= limit_usd,
    }


async def record_spend(
    repo: AsyncRepository,
    amount: float,
    kind: str = "llm_usd",
    day: str | None = None,
) -> float:
    """Increment budget consumption for the given day and return updated total."""
    target_day = day or get_malaysia_today()
    return await repo.increment_budget(day=target_day, kind=kind, amount=amount)

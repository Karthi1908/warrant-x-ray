"""Usage and cost logging coordinator.

Implements FR-CTRL-02, FR-CTRL-03:
- Captures LLM invocation metrics (model, tier, tokens, latency, cost).
- Deducts token spend against daily budgets in Malaysia time.
- Guarantees no PII or raw IP addresses are persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING

from warrantx.llm.pricing import calculate_token_cost_usd

if TYPE_CHECKING:
    from warrantx.data.repo import AsyncRepository, LlmCall

_KL_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def get_malaysia_today() -> str:
    """Return current date in Malaysia time formatted as YYYY-MM-DD."""
    return datetime.now(_KL_TZ).strftime("%Y-%m-%d")


@dataclass
class UsageMetricsData:
    model: str
    tier: str
    purpose: str
    in_tokens: int = 0
    out_tokens: int = 0
    reasoning_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    status: str = "ok"
    turn_id: str | None = None
    session_hash: str | None = None


async def record_usage(
    repo: AsyncRepository,
    model: str,
    tier: str,
    purpose: str,
    in_tokens: int = 0,
    out_tokens: int = 0,
    reasoning_tokens: int = 0,
    latency_ms: int = 0,
    turn_id: str | None = None,
    session_hash: str | None = None,
    status: str = "ok",
) -> LlmCall:
    """Calculate cost, log the LLM invocation, and increment today's budget."""
    cost = calculate_token_cost_usd(
        model=model,
        in_tokens=in_tokens,
        out_tokens=out_tokens,
        reasoning_tokens=reasoning_tokens,
    )

    day = get_malaysia_today()

    call_record = await repo.log_llm_call(
        model=model,
        tier=tier,
        purpose=purpose,
        in_tokens=in_tokens,
        out_tokens=out_tokens,
        reasoning_tokens=reasoning_tokens,
        latency_ms=latency_ms,
        cost_usd=cost,
        status=status,
        turn_id=turn_id,
        session_hash=session_hash,
    )

    if cost > 0:
        await repo.increment_budget(day=day, kind="llm_usd", amount=cost)

    return call_record

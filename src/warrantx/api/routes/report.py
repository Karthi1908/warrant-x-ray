"""Deep Risk Report routes (T106, FR-DEEP-01 to 06, AC-17).

Provides:
- GET /api/report/{report_id}: Retrieve stored deep report by composite key.
- POST /api/report: Run 4-stage SequentialAgent generation with session cap and caching.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from warrantx.agents.deep_report import SequentialAgent
from warrantx.api.errors import InvalidInputError, NotFoundError, RateLimitError
from warrantx.llm.models import get_model

router = APIRouter(prefix="/api", tags=["report"])


class DeepReportRequest(BaseModel):
    """Payload for generating a deep risk report."""

    code: str
    holding_days: int = Field(default=5, ge=1, le=365)
    snapshot_id: int | None = None


@router.get("/report/{report_id}")
async def get_report(report_id: str, request: Request) -> dict[str, Any]:
    """Retrieve a stored deep risk report by ID (code_snapshot_holding)."""
    repo = getattr(request.app.state, "repo", None)
    if not repo:
        raise NotFoundError("Repository persistence is unavailable.")

    clean_id = report_id.strip()
    parts = clean_id.replace("-", "_").split("_")
    code = parts[0].upper()

    snapshot_id = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else None
    holding_days = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 5

    if snapshot_id is None:
        latest = await repo.get_latest_good_snapshot()
        if not latest:
            raise NotFoundError(f"No snapshot found to load report for '{code}'.")
        snapshot_id = latest.id

    report = await repo.get_report(code, snapshot_id, holding_days)
    if not report:
        raise NotFoundError(f"Deep Risk Report '{clean_id}' not found.")

    return {
        "report_id": clean_id,
        "report": report,
        "cached": True,
    }


@router.post("/report")
async def create_deep_report(req: DeepReportRequest, request: Request) -> dict[str, Any]:
    """Generate or retrieve cached Deep Risk Report (FR-DEEP-01 to 06)."""
    repo = getattr(request.app.state, "repo", None)
    if not repo:
        raise NotFoundError("Repository persistence is unavailable.")

    # Record interactive query count (FR-020)
    try:
        await repo.record_interactive_query()
    except Exception:
        pass

    session_id = request.headers.get("X-Session-ID") or "anonymous"
    settings = getattr(request.app.state, "settings", None)
    llm = get_model("super", settings=settings)
    news_service = getattr(request.app.state, "news_service", None)

    agent = SequentialAgent(llm=llm, repo=repo, news_service=news_service)
    result = await agent.generate_report(
        code=req.code,
        holding_days=req.holding_days,
        snapshot_id=req.snapshot_id,
        session_id=session_id,
    )

    if not result.get("ok"):
        if result.get("error") == "rate_limited":
            raise RateLimitError(result["message"])
        if result.get("error") == "not_found":
            raise NotFoundError(result["message"])
        raise InvalidInputError(result.get("message", "Could not generate report."))

    return result

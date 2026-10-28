"""Meta routes providing system status, model info, data staleness, and anonymous usage (T080)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from warrantx.api.chat_gate import is_local_request
from warrantx.config import get_settings
from warrantx.data.staleness import evaluate_data_staleness

router = APIRouter(prefix="/api", tags=["meta"])


class PublicUsageMetrics(BaseModel):
    """Publicly exposed aggregated usage counts."""

    total_visits: int = 0
    daily_uniques: int = 0
    interactive_queries: int = 0
    visits: int = 0
    unique_visitors_daily: int = 0


class SnapshotSummary(BaseModel):
    """Summary of a stored market data snapshot."""

    id: int
    fetched_at: str
    row_count: int = 0
    collector_source: str = "direct_screener"
    ok: bool = True
    note: str = ""


class SnapshotsResponse(BaseModel):
    """List of stored snapshots."""

    snapshots: list[SnapshotSummary] = Field(default_factory=list)


class MetaResponse(BaseModel):
    """System metadata response."""

    version: str = "0.1.0"
    mode: str = Field(description="Operational mode: live, replay, sample")
    as_of: str = Field(description="UTC timestamp of current market data")
    collector_source: str = Field(
        default="direct_screener",
        description="Source of current snapshot: tavily_crawl | direct_screener | stored_replay | synthetic_sample",
    )
    market_open: bool = False
    stale: bool = False
    staleness_seconds: int = 0
    last_collection_status: str = "ok"
    resolved_model_ids: dict[str, str] = Field(default_factory=dict)
    tier_health: dict[str, str] = Field(default_factory=dict)
    usage_metrics: PublicUsageMetrics = Field(default_factory=PublicUsageMetrics)
    chat_enabled: bool = False


@router.get("/meta", response_model=MetaResponse)
async def get_meta(request: Request) -> MetaResponse:
    """Return operational metadata, model status, staleness, and public usage counts."""
    settings = getattr(request.app.state, "settings", None) or get_settings()
    repo = getattr(request.app.state, "repo", None)

    usage = PublicUsageMetrics()
    today_my = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    as_of = datetime.now(timezone.utc).isoformat()
    mode = getattr(request.app.state, "mode", settings.mode)
    market_open = False
    stale = False
    staleness_seconds = 0
    last_status = "ok"
    collector_source = "direct_screener"

    if repo:
        m = await repo.get_usage_metrics(today_my)
        if m:
            usage = PublicUsageMetrics(
                total_visits=m.visit_count,
                daily_uniques=m.unique_visitor_count,
                interactive_queries=m.interactive_query_count,
                visits=m.visit_count,
                unique_visitors_daily=m.unique_visitor_count,
            )

        latest = await repo.get_latest_good_snapshot()
        if latest:
            collector_source = getattr(latest, "collector_source", "direct_screener")
            if hasattr(latest.fetched_at, "isoformat"):
                as_of = latest.fetched_at.isoformat()
            else:
                as_of = str(latest.fetched_at)

            eval_res = evaluate_data_staleness(
                fetched_at=latest.fetched_at,
                has_live_feed=(mode == "live"),
                default_mode=mode,
            )
            mode = eval_res.mode
            market_open = eval_res.market_open
            stale = eval_res.is_stale
            staleness_seconds = eval_res.staleness_seconds
            last_status = "ok" if latest.ok else "error"
        else:
            mode = "sample"

    chat_enabled = is_local_request(request, settings)

    return MetaResponse(
        version="0.1.0",
        mode=mode,
        as_of=as_of,
        collector_source=collector_source,
        market_open=market_open,
        stale=stale,
        staleness_seconds=staleness_seconds,
        last_collection_status=last_status,
        resolved_model_ids={
            "nano": settings.model_nano,
            "super": settings.model_super,
            "ultra": settings.model_ultra,
        },
        tier_health={
            "nano": "healthy",
            "super": "healthy",
            "ultra": "healthy",
        },
        usage_metrics=usage,
        chat_enabled=chat_enabled,
    )


@router.get("/snapshots", response_model=SnapshotsResponse)
async def get_snapshots(request: Request) -> SnapshotsResponse:
    """Return list of available historical snapshots (T080)."""
    repo = getattr(request.app.state, "repo", None)
    if not repo:
        return SnapshotsResponse(snapshots=[])

    snaps = await repo.list_snapshots(limit=50)
    result = [
        SnapshotSummary(
            id=s.id,
            fetched_at=s.fetched_at.isoformat()
            if hasattr(s.fetched_at, "isoformat")
            else str(s.fetched_at),
            row_count=s.row_count,
            collector_source=getattr(s, "collector_source", "direct_screener"),
            ok=s.ok,
            note=s.note or "",
        )
        for s in snaps
    ]
    return SnapshotsResponse(snapshots=result)

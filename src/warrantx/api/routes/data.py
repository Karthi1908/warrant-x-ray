"""Market data routes: underlyings, search, card, scenario, stock overview, compare, news."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import BaseModel, Field

from warrantx.api.errors import InvalidInputError, NotFoundError
from warrantx.tools.models import ScenarioInputs, ScenarioResult, WarrantCard

router = APIRouter(prefix="/api", tags=["data"])


class CompareRequest(BaseModel):
    """Request payload for comparing warrants."""

    codes: list[str] = Field(min_length=2, max_length=3, description="2 to 3 warrant codes")
    holding_days: int = Field(default=5, ge=1, le=365)


class ExplainMoveRequest(BaseModel):
    """Request payload for mid price change attribution."""

    code: str
    from_snapshot_id: int
    to_snapshot_id: int


@router.get("/underlyings")
async def list_underlyings(
    request: Request, snapshot_id: int | None = Query(default=None)
) -> dict[str, Any]:
    """List Malaysian underlying assets with warrant counts."""
    repo = getattr(request.app.state, "repo", None)
    mode = getattr(request.app.state, "mode", "sample")
    as_of = datetime.now(timezone.utc).isoformat()

    if not repo:
        return {"underlyings": [], "as_of": as_of, "mode": mode}

    snapshot = (
        await repo.get_snapshot(snapshot_id)
        if snapshot_id is not None
        else await repo.get_latest_good_snapshot()
    )
    if snapshot:
        as_of = snapshot.fetched_at.isoformat()
        rows = await repo.list_all_warrants(snapshot_id=snapshot.id, valid_only=True)
    else:
        rows = []

    # Map underlying ticker to call/put counts and prices
    counts: dict[str, dict[str, Any]] = {}
    for r in rows:
        tk = r.underlying_ticker.upper()
        if tk not in counts:
            counts[tk] = {"calls": 0, "puts": 0, "total": 0, "price": r.underlying_bid}
        counts[tk]["total"] += 1
        if r.type.lower() == "call":
            counts[tk]["calls"] += 1
        elif r.type.lower() == "put":
            counts[tk]["puts"] += 1

    items = await repo.list_underlyings()
    underlyings_map = {u.ticker.upper(): u for u in items}

    all_tickers = sorted(list(set(list(underlyings_map.keys()) + list(counts.keys()))))
    results = []
    for tk in all_tickers:
        meta = underlyings_map.get(tk)
        cnt = counts.get(tk, {"calls": 0, "puts": 0, "total": 0, "price": None})
        results.append({
            "ticker": tk,
            "code": meta.code if meta else "",
            "name": meta.name if meta else tk,
            "call_count": cnt["calls"],
            "put_count": cnt["puts"],
            "total_warrants": cnt["total"],
            "price": cnt["price"],
        })

    return {
        "underlyings": results,
        "as_of": as_of,
        "mode": mode,
    }


@router.get("/warrants")
async def search_warrants(
    request: Request,
    underlying: str | None = Query(default=None),
    type: str | None = Query(default=None),
    issuer: str | None = Query(default=None),
    min_days: int | None = Query(default=None),
    max_days: int | None = Query(default=None),
    moneyness: str | None = Query(default=None),
    sort_by: str = Query(default="effective_gearing"),
    order: str = Query(default="desc"),
    limit: int = Query(default=10, ge=1, le=100),
    iv_basis: str = Query(default="mid"),
    snapshot_id: int | None = Query(default=None),
) -> dict[str, Any]:
    """Search structured warrants with filtering, quantitative metrics, and sorting."""
    from datetime import date
    from warrantx.quant.metrics import WarrantQuantInput, compute_metrics
    from warrantx.tools.evidence import format_currency, format_days, format_percent, format_ratio

    repo = getattr(request.app.state, "repo", None)
    mode = getattr(request.app.state, "mode", "sample")
    as_of = datetime.now(timezone.utc).isoformat()

    if not repo:
        return {"results": [], "count": 0, "as_of": as_of, "mode": mode}

    snapshot = (
        await repo.get_snapshot(snapshot_id)
        if snapshot_id is not None
        else await repo.get_latest_good_snapshot()
    )
    if not snapshot:
        return {"results": [], "count": 0, "as_of": as_of, "mode": mode}

    as_of = snapshot.fetched_at.isoformat()
    as_of_d = date.fromisoformat(as_of[:10]) if len(as_of) >= 10 else date.today()

    if underlying:
        clean_und = underlying.strip().upper()
        raw_rows = await repo.list_warrants_for_underlying(clean_und, snapshot_id=snapshot.id, valid_only=True)
    else:
        raw_rows = await repo.list_all_warrants(snapshot_id=snapshot.id, valid_only=True)

    filtered_rows = []
    for r in raw_rows:
        if type and r.type.lower() != type.lower():
            continue
        if issuer and r.issuer.upper() != issuer.upper():
            continue

        try:
            exp_d = date.fromisoformat(r.expiry_date)
            days_left = max(0, (exp_d - as_of_d).days)
        except Exception:
            days_left = 0

        if min_days is not None and days_left < min_days:
            continue
        if max_days is not None and days_left > max_days:
            continue

        if moneyness and r.underlying_bid and r.underlying_bid > 0:
            m_val = r.underlying_bid / r.strike if r.type.lower() == "call" else r.strike / r.underlying_bid
            if moneyness == "itm" and m_val <= 1.0:
                continue
            elif moneyness == "otm" and m_val >= 1.0:
                continue
            elif moneyness == "atm" and not (0.95 <= m_val <= 1.05):
                continue

        filtered_rows.append((r, days_left))

    enriched: list[dict[str, Any]] = []
    for r, days_left in filtered_rows:
        u_price = (
            r.underlying_bid
            if r.underlying_bid and r.underlying_bid > 0
            else (r.strike if r.strike > 0 else 10.0)
        )
        q_inp = WarrantQuantInput(
            code=r.code,
            issuer=r.issuer,
            type=r.type.lower(),  # type: ignore[arg-type]
            underlying_price=u_price,
            strike=r.strike,
            ratio=r.ratio_raw,
            bid=r.bid,
            ask=r.ask,
            last=r.last_price,
            days_to_expiry=max(0, days_left),
            risk_free_rate=0.03,
            issuer_iv=r.issuer_iv,
            issuer_eg=r.issuer_eg,
        )
        m = compute_metrics(q_inp)
        spread_pct = m.spread_pct
        eg = m.effective_gearing or r.issuer_eg
        iv = m.headline_iv or (r.issuer_iv / 100.0 if r.issuer_iv else None)

        enriched.append({
            "code": r.code,
            "issuer": r.issuer,
            "type": r.type,
            "underlying_ticker": r.underlying_ticker,
            "expiry_date": r.expiry_date,
            "days_to_expiry": days_left,
            "display_days_to_expiry": format_days(days_left),
            "strike": r.strike,
            "display_strike": format_currency(r.strike) or f"RM {r.strike:.2f}",
            "ratio": r.ratio_raw,
            "display_ratio": format_ratio(r.ratio_raw) or f"{r.ratio_raw}x",
            "bid": r.bid,
            "display_bid": format_currency(r.bid),
            "ask": r.ask,
            "display_ask": format_currency(r.ask),
            "mid": m.mid,
            "display_mid": format_currency(m.mid),
            "spread_pct": spread_pct,
            "display_spread_pct": format_percent(spread_pct),
            "effective_gearing": eg,
            "display_effective_gearing": format_ratio(eg),
            "headline_iv": iv,
            "display_headline_iv": format_percent(iv),
            "sensitivity_ticks": r.sensitivity_ticks,
        })

    reverse = (order.lower() == "desc")
    if sort_by in ("effective_gearing", "gearing"):
        enriched.sort(key=lambda x: (x.get("effective_gearing") is not None, x.get("effective_gearing") or 0.0), reverse=reverse)
    elif sort_by in ("spread_pct", "spread"):
        enriched.sort(key=lambda x: (x.get("spread_pct") is not None, x.get("spread_pct") or 999.0), reverse=reverse)
    elif sort_by == "strike":
        enriched.sort(key=lambda x: x.get("strike", 0.0), reverse=reverse)
    elif sort_by == "expiry_date":
        enriched.sort(key=lambda x: x.get("expiry_date", ""), reverse=reverse)
    elif sort_by in ("headline_iv", "iv"):
        enriched.sort(key=lambda x: (x.get("headline_iv") is not None, x.get("headline_iv") or 0.0), reverse=reverse)

    paged = enriched[:limit]
    return {
        "results": paged,
        "count": len(paged),
        "total_matches": len(enriched),
        "as_of": as_of,
        "mode": mode,
        "message": f"Found {len(enriched)} warrants" if enriched else f"No warrants found for '{underlying or ''}'",
    }


from warrantx.tools.warrants import build_warrant_card


@router.get("/warrants/{code}")
async def get_warrant_card(
    code: str,
    request: Request,
    response: Response,
    holding_days: int = Query(default=5, ge=1),
    snapshot_id: int | None = Query(default=None),
    iv_basis: str = Query(default="mid"),
    if_none_match: str | None = Header(default=None),
) -> dict[str, Any]:
    """Retrieve full warrant card with cost-of-holding presets and risk flags."""
    clean_code = code.strip().upper()
    repo = getattr(request.app.state, "repo", None)
    if not repo:
        raise NotFoundError(f"Warrant {clean_code} not found")

    if snapshot_id is not None:
        snap = await repo.get_snapshot_by_id(snapshot_id)
        if not snap:
            raise NotFoundError(f"Snapshot {snapshot_id} not found")

    warrant = await repo.get_warrant(clean_code, snapshot_id=snapshot_id)
    if not warrant:
        raise NotFoundError(f"Warrant {clean_code} not found")

    etag = f'"{warrant.snapshot_id}-{clean_code}-{holding_days}"'
    if if_none_match == etag:
        response.status_code = 304
        return {}

    response.headers["ETag"] = etag
    mode = getattr(request.app.state, "mode", "sample")
    as_of = datetime.now(timezone.utc).isoformat()
    card, _ = build_warrant_card(
        warrant, holding_days=holding_days, as_of=as_of, mode=mode
    )
    return card.model_dump()


from warrantx.tools.scenario import execute_scenario
from warrantx.quant.scenario import ScenarioError


@router.post("/scenario")
async def run_scenario(scenario_in: ScenarioInputs, request: Request) -> dict[str, Any]:
    """Execute scenario simulation (identical logic between chat tool and UI panel)."""
    repo = getattr(request.app.state, "repo", None)
    if not repo:
        raise NotFoundError("Database repository not initialized")

    try:
        result, _ = await execute_scenario(
            repo=repo,
            code=scenario_in.code,
            move=scenario_in.move,
            days=scenario_in.days,
            iv_shift=scenario_in.iv_shift,
        )
        return result.model_dump()
    except ScenarioError as err:
        raise InvalidInputError(str(err))



@router.post("/compare")
async def compare_warrants(
    compare_in: CompareRequest,
    request: Request,
    snapshot_id: int | None = Query(default=None),
) -> dict[str, Any]:
    """Compare 2 or 3 warrants on the same underlying stock in a uniform table without ranking."""
    from warrantx.tools.compare import compare_warrants as execute_compare

    repo = getattr(request.app.state, "repo", None)
    if not repo:
        raise NotFoundError("Repository not initialized")

    mode = getattr(request.app.state, "mode", "sample")

    res_dict, _ = await execute_compare(
        codes=compare_in.codes,
        repo=repo,
        holding_days=compare_in.holding_days,
        snapshot_id=snapshot_id,
        mode=mode,
    )
    return res_dict


@router.get("/stock/{ticker}")
async def get_stock_summary(
    ticker: str,
    request: Request,
    holding_days: int = Query(default=5, ge=1),
    snapshot_id: int | None = Query(default=None),
) -> dict[str, Any]:
    """Overview of warrants on a given underlying stock."""
    from warrantx.tools.stock import get_stock_summary as execute_stock_summary

    repo = getattr(request.app.state, "repo", None)
    if not repo:
        raise NotFoundError("Repository not initialized")

    summary, _ = await execute_stock_summary(
        ticker=ticker,
        repo=repo,
        holding_days=holding_days,
        snapshot_id=snapshot_id,
    )
    return summary.model_dump()


@router.get("/news")
async def get_news(
    request: Request,
    ticker: str | None = Query(default=None),
    query: str | None = Query(default=None),
    max_results: int = Query(default=6, ge=1, le=6),
) -> dict[str, Any]:
    """Fetch 7-day recency news items with multi-domain corroboration and evidence envelope."""
    from warrantx.tools.news import search_news as execute_search_news

    repo = getattr(request.app.state, "repo", None)
    news_service = getattr(request.app.state, "news_service", None)
    mode = getattr(request.app.state, "mode", "sample")

    clean_ticker = (ticker or query or "MAYBANK").strip().upper()

    result_dict, evidence = await execute_search_news(
        ticker=clean_ticker,
        query=query,
        service=news_service,
        repo=repo,
        mode=mode,
    )

    items = result_dict.get("news", [])[:max_results]
    return {
        "ticker": clean_ticker,
        "news": items,
        "count": len(items),
        "recency_window_days": 7,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "mode": result_dict.get("mode", mode),
        "evidence": evidence.model_dump(),
    }


@router.post("/explain-move")
async def explain_move(req: ExplainMoveRequest, request: Request) -> dict[str, Any]:
    """Decompose warrant mid price change across underlying, time, vol, and residual (FR-EXP-01 to 03)."""
    repo = getattr(request.app.state, "repo", None)
    if not repo:
        raise NotFoundError("Repository persistence is unavailable.")

    # Record interactive query count (FR-020)
    try:
        await repo.record_interactive_query()
    except Exception:
        pass

    from warrantx.tools.explain import execute_explain_move

    attribution, evidence = await execute_explain_move(
        repo=repo,
        code=req.code,
        from_snapshot_id=req.from_snapshot_id,
        to_snapshot_id=req.to_snapshot_id,
    )

    return {
        "attribution": attribution.model_dump(),
        "evidence": evidence.model_dump(),
        "mode": getattr(request.app.state, "mode", "sample"),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/snapshots")
async def list_snapshots(request: Request) -> dict[str, Any]:
    """List stored snapshots."""
    return {
        "snapshots": [],
        "as_of": datetime.now(timezone.utc).isoformat(),
    }

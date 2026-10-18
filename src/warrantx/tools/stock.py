"""Stock summary and warrant overview analytical tool (T094, FR-STK-01..05).

Provides stock-level warrant metrics:
- Call and put counts
- Active issuers
- Median bid/ask spread and flat-underlying decay
- Aggregated risk flag counts
- Up to 5 nearest-to-the-money warrants sorted by absolute strike distance
- 10-day and 30-day realized volatility if price history is available
"""

from __future__ import annotations

import statistics
from datetime import date, datetime, timezone
from typing import Any

from warrantx.data.repo import AsyncRepository, WarrantRow
from warrantx.quant.flags import compute_holding_cost_presets, evaluate_flags
from warrantx.quant.metrics import WarrantQuantInput, compute_metrics
from warrantx.quant.vol import compute_realized_volatility
from warrantx.tools.warrants import build_warrant_card
from warrantx.tools.evidence import (
    Evidence,
    format_currency,
    format_days,
    format_percent,
    format_ratio,
)
from warrantx.tools.models import NearestWarrant, StockSummary


async def get_stock_summary(
    ticker: str,
    repo: AsyncRepository,
    holding_days: int = 5,
    snapshot_id: int | None = None,
    turn_id: str = "",
    evidence_index: int = 1,
) -> tuple[StockSummary, Evidence]:
    """Build stock-level warrant summary and Evidence record."""
    clean_ticker = ticker.strip().upper()

    snapshot = (
        await repo.get_snapshot(snapshot_id)
        if snapshot_id is not None
        else await repo.get_latest_good_snapshot()
    )

    as_of = (
        snapshot.fetched_at.isoformat()
        if snapshot
        else datetime.now(timezone.utc).isoformat()
    )
    ev_id = f"E{evidence_index}"

    if not snapshot:
        empty_res = StockSummary(
            ticker=clean_ticker,
            as_of=as_of,
            evidence_id=ev_id,
        )
        ev = Evidence.wrap(
            evidence_id=ev_id,
            kind="stock_summary",
            source="repository",
            payload=empty_res.model_dump(),
            summary=f"Overview of warrants for {clean_ticker} (no data)",
            turn_id=turn_id or None,
        )
        return empty_res, ev

    rows = await repo.list_warrants_for_underlying(
        clean_ticker, snapshot_id=snapshot.id, valid_only=True
    )

    if not rows:
        empty_res = StockSummary(
            ticker=clean_ticker,
            as_of=as_of,
            evidence_id=ev_id,
        )
        ev = Evidence.wrap(
            evidence_id=ev_id,
            kind="stock_summary",
            source="repository",
            payload=empty_res.model_dump(),
            summary=f"Overview of warrants for {clean_ticker} (0 warrants available)",
            turn_id=turn_id or None,
        )
        return empty_res, ev

    # Extract underlying price
    prices = [r.underlying_bid for r in rows if r.underlying_bid and r.underlying_bid > 0]
    underlying_price = prices[0] if prices else None

    # Counts and metadata
    call_count = sum(1 for r in rows if r.type.lower() == "call")
    put_count = sum(1 for r in rows if r.type.lower() == "put")
    issuers = sorted(list(set(r.issuer for r in rows if r.issuer)))

    expiries = [r.expiry_date for r in rows if r.expiry_date]
    min_expiry = min(expiries) if expiries else None
    max_expiry = max(expiries) if expiries else None

    # Compute metrics for medians and nearest warrants
    as_of_d = date.fromisoformat(as_of[:10]) if len(as_of) >= 10 else date.today()
    spread_pcts: list[float] = []
    flat_decays: list[float] = []
    flag_counts: dict[str, int] = {}
    nearest_candidates: list[tuple[float, NearestWarrant]] = []

    for r in rows:
        card, _ = build_warrant_card(
            row=r,
            holding_days=holding_days,
            as_of=as_of,
        )

        if card.metrics.spread_pct is not None:
            spread_pcts.append(card.metrics.spread_pct)

        if card.presets.flat_decay is not None:
            flat_decays.append(card.presets.flat_decay)

        for f in card.flags:
            flag_counts[f.code] = flag_counts.get(f.code, 0) + 1

        # Nearest to the money distance
        if underlying_price:
            dist = abs(underlying_price - card.strike)
            nw = NearestWarrant(
                code=card.code,
                type=card.type,
                strike=card.strike,
                display_strike=card.display_strike,
                distance_from_strike=dist,
                display_distance_from_strike=format_currency(dist) or f"RM {dist:.2f}",
                bid=card.bid,
                display_bid=card.display_bid,
                ask=card.ask,
                display_ask=card.display_ask,
                days_to_expiry=card.metrics.days_to_expiry,
                display_days_to_expiry=card.metrics.display_days_to_expiry,
                effective_gearing=card.metrics.effective_gearing,
                display_effective_gearing=card.metrics.display_effective_gearing,
            )
            nearest_candidates.append((dist, nw))

    # Sort nearest by strike distance ascending
    nearest_candidates.sort(key=lambda x: x[0])
    nearest_warrants = [item[1] for item in nearest_candidates[:5]]

    median_spread = statistics.median(spread_pcts) if spread_pcts else None
    median_decay = statistics.median(flat_decays) if flat_decays else None

    # Realized vol if available from history
    vol_10d: float | None = None
    vol_30d: float | None = None
    try:
        history_rows = await repo.get_history(clean_ticker, days=45)
        closes = [h.close for h in history_rows if h.close and h.close > 0]
        if len(closes) >= 11:
            vol_10d = compute_realized_volatility(closes[-11:])
        if len(closes) >= 31:
            vol_30d = compute_realized_volatility(closes[-31:])
    except Exception:
        pass

    summary = StockSummary(
        ticker=clean_ticker,
        price=underlying_price,
        display_price=format_currency(underlying_price),
        as_of=as_of,
        call_count=call_count,
        put_count=put_count,
        issuer_count=len(issuers),
        issuers=issuers,
        min_expiry=min_expiry,
        max_expiry=max_expiry,
        median_spread_pct=median_spread,
        display_median_spread_pct=format_percent(median_spread),
        median_flat_decay=median_decay,
        display_median_flat_decay=format_currency(median_decay),
        flag_counts=flag_counts,
        realized_vol_10d=vol_10d,
        display_realized_vol_10d=format_percent(vol_10d),
        realized_vol_30d=vol_30d,
        display_realized_vol_30d=format_percent(vol_30d),
        nearest_warrants=nearest_warrants,
        evidence_id=ev_id,
    )

    ev = Evidence.wrap(
        evidence_id=ev_id,
        kind="stock_summary",
        source="repository",
        payload=summary.model_dump(),
        summary=f"Stock overview for {clean_ticker}: {len(rows)} warrants ({call_count} calls, {put_count} puts)",
        turn_id=turn_id or None,
    )

    return summary, ev

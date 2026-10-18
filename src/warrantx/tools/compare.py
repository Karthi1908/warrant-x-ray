"""Uniform warrant comparison tool without ranking or recommendation (T094, FR-CMP-01..04, AC-05).

Enforces:
- 2 to 3 warrants strictly.
- Same underlying stock required (mixed underlyings rejected).
- Fixed-attribute uniform comparison table with identical ordering.
- NO 'best', 'ranking', or recommendation tags (Constitution Principle III).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from warrantx.api.errors import InvalidInputError, NotFoundError
from warrantx.data.repo import AsyncRepository
from warrantx.tools.evidence import Evidence
from warrantx.tools.warrants import build_warrant_card


class ComparedWarrantItem(BaseModel):
    """Uniform fixed-attribute comparison item for a single warrant."""

    code: str
    issuer: str
    type: str
    underlying_ticker: str
    underlying_price: float | None = None
    display_underlying_price: str | None = None
    strike: float
    display_strike: str
    ratio: float
    display_ratio: str
    expiry_date: str
    days_to_expiry: int | None = None
    display_days_to_expiry: str | None = None
    bid: float | None = None
    display_bid: str | None = None
    ask: float | None = None
    display_ask: str | None = None
    mid: float | None = None
    display_mid: str | None = None
    spread_pct: float | None = None
    display_spread_pct: str | None = None
    effective_gearing: float | None = None
    display_effective_gearing: str | None = None
    headline_iv: float | None = None
    display_headline_iv: str | None = None
    spread_cost: float | None = None
    display_spread_cost: str | None = None
    flat_decay: float | None = None
    display_flat_decay: str | None = None
    iv_crush: float | None = None
    display_iv_crush: str | None = None
    breakeven_move: float | None = None
    display_breakeven_move: str | None = None
    flags: list[dict[str, Any]] = Field(default_factory=list)


class WarrantComparisonResult(BaseModel):
    """Overall comparison container."""

    underlying_ticker: str
    holding_days: int
    comparison: list[ComparedWarrantItem]
    as_of: str
    mode: str = "sample"
    evidence_id: str = ""


async def compare_warrants(
    codes: list[str],
    repo: AsyncRepository,
    holding_days: int = 5,
    snapshot_id: int | None = None,
    mode: str = "sample",
    turn_id: str = "",
    evidence_index: int = 1,
) -> tuple[dict[str, Any], Evidence]:
    """Compare 2 to 3 warrants uniformly on the same underlying stock."""
    # 1. Size checks
    clean_codes = [c.strip().upper() for c in codes if c and c.strip()]
    if len(clean_codes) < 2:
        raise InvalidInputError("Comparison requires at least 2 warrants")
    if len(clean_codes) > 3:
        raise InvalidInputError("Comparison allows at most 3 warrants")

    snapshot = (
        await repo.get_snapshot(snapshot_id)
        if snapshot_id is not None
        else await repo.get_latest_good_snapshot()
    )
    if not snapshot:
        raise NotFoundError("No snapshot available for comparison")

    as_of = snapshot.fetched_at.isoformat()

    # 2. Fetch rows
    rows = []
    for code in clean_codes:
        row = await repo.get_warrant(code, snapshot_id=snapshot.id)
        if not row:
            raise NotFoundError(f"Warrant code '{code}' not found")
        rows.append(row)

    # 3. Check for mixed underlyings
    underlyings = set(r.underlying_ticker for r in rows)
    if len(underlyings) > 1:
        raise InvalidInputError(
            f"Comparison requires warrants on the same underlying stock. Found mixed underlyings: {', '.join(sorted(underlyings))}"
        )

    common_underlying = list(underlyings)[0]

    # 4. Build uniform cards
    compared_items: list[ComparedWarrantItem] = []
    for r in rows:
        card, _ = build_warrant_card(
            row=r,
            holding_days=holding_days,
            as_of=as_of,
            mode=mode,
        )

        item = ComparedWarrantItem(
            code=card.code,
            issuer=card.issuer,
            type=card.type,
            underlying_ticker=card.underlying_ticker,
            underlying_price=card.underlying_price,
            display_underlying_price=card.display_underlying_price,
            strike=card.strike,
            display_strike=card.display_strike,
            ratio=card.ratio_raw,
            display_ratio=card.display_ratio,
            expiry_date=card.expiry_date,
            days_to_expiry=card.metrics.days_to_expiry,
            display_days_to_expiry=card.metrics.display_days_to_expiry,
            bid=card.bid,
            display_bid=card.display_bid,
            ask=card.ask,
            display_ask=card.display_ask,
            mid=card.metrics.mid,
            display_mid=card.metrics.display_mid,
            spread_pct=card.metrics.spread_pct,
            display_spread_pct=card.metrics.display_spread_pct,
            effective_gearing=card.metrics.effective_gearing,
            display_effective_gearing=card.metrics.display_effective_gearing,
            headline_iv=card.metrics.headline_iv,
            display_headline_iv=card.metrics.display_headline_iv,
            spread_cost=card.presets.spread_cost,
            display_spread_cost=card.presets.display_spread_cost,
            flat_decay=card.presets.flat_decay,
            display_flat_decay=card.presets.display_flat_decay,
            iv_crush=card.presets.iv_crush,
            display_iv_crush=card.presets.display_iv_crush,
            breakeven_move=card.presets.breakeven_move,
            display_breakeven_move=card.presets.display_breakeven_move,
            flags=[f.model_dump() for f in card.flags],
        )
        compared_items.append(item)

    ev_id = f"E{evidence_index}"
    result = WarrantComparisonResult(
        underlying_ticker=common_underlying,
        holding_days=holding_days,
        comparison=compared_items,
        as_of=as_of,
        mode=mode,
        evidence_id=ev_id,
    )
    res_dict = result.model_dump()

    evidence = Evidence.wrap(
        evidence_id=ev_id,
        kind="comparison",
        source="repository",
        payload=res_dict,
        summary=f"Comparison of {len(compared_items)} warrants on {common_underlying} for {holding_days}-day hold",
        turn_id=turn_id or None,
    )

    if turn_id:
        await repo.save_evidence(
            turn_id=turn_id,
            evidence_id=ev_id,
            kind="comparison",
            source="repository",
            payload_json=res_dict,
        )

    return res_dict, evidence

"""Warrant card builder and analytical tools.

Integrates:
- Pure quant metrics engine (Black-Scholes, Brent IV, Greeks)
- Cost-of-holding presets
- Risk flags and not_evaluated classification
- Issuer vs recomputed cross-checks
- Evidence wrapping with grounding allowlist
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from warrantx.data.repo import WarrantRow
from warrantx.quant.flags import compute_holding_cost_presets, evaluate_flags
from warrantx.quant.metrics import WarrantQuantInput, compute_metrics
from warrantx.tools.evidence import (
    Evidence,
    format_currency,
    format_percent,
    format_ratio,
)
from warrantx.tools.models import WarrantCard, WarrantRowModel


def _row_to_model(row: WarrantRow | WarrantRowModel | dict[str, Any]) -> WarrantRowModel:
    """Convert a database row or dict into a validated WarrantRowModel."""
    if isinstance(row, WarrantRowModel):
        return row

    if isinstance(row, WarrantRow):
        d = {
            "code": row.code,
            "issuer": row.issuer,
            "type": row.type,
            "underlying_ticker": row.underlying_ticker,
            "expiry_date": row.expiry_date,
            "strike": row.strike,
            "display_strike": format_currency(row.strike) or f"RM {row.strike:.2f}",
            "ratio_raw": row.ratio_raw,
            "display_ratio": format_ratio(row.ratio_raw) or f"{row.ratio_raw}x",
            "underlying_bid": row.underlying_bid,
            "display_underlying_bid": format_currency(row.underlying_bid),
            "bid": row.bid,
            "display_bid": format_currency(row.bid),
            "ask": row.ask,
            "display_ask": format_currency(row.ask),
            "bid_volume": row.bid_volume,
            "ask_volume": row.ask_volume,
            "traded_volume": row.traded_volume,
            "last_price": row.last_price,
            "display_last_price": format_currency(row.last_price),
            "last_time": row.last_time,
            "issuer_iv": row.issuer_iv,
            "display_issuer_iv": format_percent(row.issuer_iv / 100.0) if row.issuer_iv else None,
            "issuer_eg": row.issuer_eg,
            "display_issuer_eg": format_ratio(row.issuer_eg),
            "issuer_delta": row.issuer_delta,
            "display_issuer_delta": f"{row.issuer_delta:.3f}" if row.issuer_delta else None,
            "issuer_premium": row.issuer_premium,
            "display_issuer_premium": (
                format_percent(row.issuer_premium / 100.0) if row.issuer_premium else None
            ),
            "issuer_theta_raw": row.issuer_theta_raw,
            "display_issuer_theta_raw": (
                format_currency(row.issuer_theta_raw) if row.issuer_theta_raw else None
            ),
            "sensitivity_ticks": row.sensitivity_ticks,
            "moneyness": row.moneyness,
            "indicators": row.indicators,
            "valid": row.valid,
        }
        return WarrantRowModel(**d)

    # Dictionary input
    d = dict(row)
    if "display_strike" not in d:
        d["display_strike"] = format_currency(d.get("strike")) or f"RM {d.get('strike'):.2f}"
    if "display_ratio" not in d:
        d["display_ratio"] = format_ratio(d.get("ratio_raw")) or f"{d.get('ratio_raw')}x"
    return WarrantRowModel(**d)


def build_warrant_card(
    row: WarrantRow | WarrantRowModel | dict[str, Any],
    holding_days: int = 5,
    as_of: str | None = None,
    mode: str = "live",
    evidence_id: str = "E1",
    realized_vol_30d: float | None = None,
) -> tuple[WarrantCard, Evidence]:
    """Construct full WarrantCard object and associated grounding Evidence."""
    row_model = _row_to_model(row)

    if as_of is None:
        as_of_dt = datetime.now(timezone.utc)
        as_of_str = as_of_dt.isoformat()
    else:
        as_of_str = as_of
        try:
            as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except Exception:
            as_of_dt = datetime.now(timezone.utc)

    # Calculate days to expiry
    try:
        exp_date = date.fromisoformat(row_model.expiry_date)
        days_left = (exp_date - as_of_dt.date()).days
    except Exception:
        days_left = 30

    is_expired = days_left <= 0

    # Build quant input
    u_price = (
        row_model.underlying_bid
        if row_model.underlying_bid and row_model.underlying_bid > 0
        else (row_model.strike if row_model.strike > 0 else 10.0)
    )

    quant_in = WarrantQuantInput(
        code=row_model.code,
        issuer=row_model.issuer,
        type=row_model.type.lower(),  # type: ignore[arg-type]
        underlying_price=u_price,
        strike=row_model.strike,
        ratio=row_model.ratio_raw,
        bid=row_model.bid,
        ask=row_model.ask,
        last=row_model.last_price,
        bid_volume=row_model.bid_volume,
        ask_volume=row_model.ask_volume,
        days_to_expiry=max(0, days_left),
        risk_free_rate=0.03,
        issuer_iv=row_model.issuer_iv,
        issuer_eg=row_model.issuer_eg,
        issuer_delta=row_model.issuer_delta,
    )

    metrics = compute_metrics(quant_in)
    presets = compute_holding_cost_presets(metrics, holding_days=holding_days)
    flags_res = evaluate_flags(
        row_model, metrics, realized_vol_30d=realized_vol_30d
    )

    card = WarrantCard(
        code=row_model.code,
        issuer=row_model.issuer,
        type=row_model.type,
        underlying_ticker=row_model.underlying_ticker,
        expiry_date=row_model.expiry_date,
        strike=row_model.strike,
        display_strike=row_model.display_strike,
        ratio_raw=row_model.ratio_raw,
        display_ratio=row_model.display_ratio,
        underlying_price=u_price,
        display_underlying_price=format_currency(u_price),
        bid=row_model.bid,
        display_bid=row_model.display_bid,
        ask=row_model.ask,
        display_ask=row_model.display_ask,
        metrics=metrics,
        holding_days=holding_days,
        presets=presets,
        flags=flags_res.flags,
        not_evaluated=flags_res.not_evaluated,
        evidence_id=evidence_id,
        as_of=as_of_str,
        mode=mode,
        expired=is_expired,
    )

    summary = (
        f"{row_model.issuer} {row_model.underlying_ticker} {row_model.type.upper()} "
        f"strike {row_model.display_strike}, expiry {row_model.expiry_date}"
    )

    evidence = Evidence.wrap(
        evidence_id=evidence_id,
        kind="card",
        source="warrant_engine",
        payload=card,
        as_of=as_of_str,
        summary=summary,
    )

    return card, evidence

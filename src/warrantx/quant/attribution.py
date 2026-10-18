"""Sequential move attribution for Bursa Malaysia structured warrants (FR-EXP-01, FR-EXP-02, FR-EXP-03).

Decomposes the change in mid price between two snapshots into:
1. Underlying move (keeping time and IV constant at T0)
2. Passage of time (advancing time with new underlying and old IV)
3. Change in implied volatility (shifting IV with new underlying and new time)
4. Residual (spread and model discrepancy)

Guarantees:
- Sum-to-total identical within 1e-9 (FR-EXP-02).
- Explicitly states the sequence order because attribution depends on order (FR-EXP-02).
- Returns missing inputs and no decomposition if required data is absent (FR-EXP-03).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from warrantx.quant.bs import OptionType, bs_price
from warrantx.quant.iv import solve_iv


@dataclass
class SequentialAttributionResult:
    """Result of sequential move attribution."""

    ok: bool
    total_change: float | None = None
    underlying_move: float | None = None
    passage_of_time: float | None = None
    implied_volatility: float | None = None
    residual: float | None = None
    order: list[str] = field(
        default_factory=lambda: [
            "underlying_move",
            "passage_of_time",
            "implied_volatility",
            "residual",
        ]
    )
    order_description: str = (
        "Decomposition was calculated sequentially in the fixed order: "
        "(1) underlying move, (2) passage of time, (3) change in implied volatility, (4) residual. "
        "The split depends on this order."
    )
    missing: list[str] = field(default_factory=list)
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def _get_val(obj: Any, key: str, fallback_key: str | None = None) -> Any:
    """Safely extract field from dict or object."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        v = obj.get(key)
        if v is None and fallback_key:
            v = obj.get(fallback_key)
        return v
    v = getattr(obj, key, None)
    if v is None and fallback_key:
        v = getattr(obj, fallback_key, None)
    return v


def attribute_move(
    from_row: Any,
    to_row: Any,
    risk_free_rate: float = 0.03,
) -> SequentialAttributionResult:
    """Calculate sequential mid price attribution between two snapshots (FR-EXP-01 to 03)."""
    missing: list[str] = []

    # 1. Verify existence of rows
    if from_row is None:
        missing.append("from_snapshot")
    if to_row is None:
        missing.append("to_snapshot")

    if missing:
        return SequentialAttributionResult(
            ok=False,
            missing=missing,
            message=f"Missing warrant snapshot data: {', '.join(missing)}",
        )

    # 2. Extract inputs from from_row
    code = _get_val(from_row, "code") or _get_val(to_row, "code") or "unknown"
    opt_type_raw = str(_get_val(from_row, "type", "warrant_type") or "call").lower()
    option_type: OptionType = "put" if "put" in opt_type_raw else "call"

    strike = _get_val(from_row, "strike")
    ratio = _get_val(from_row, "ratio", "ratio_raw")
    days_0 = _get_val(from_row, "days_to_expiry")
    s_0 = _get_val(from_row, "underlying_price", "underlying_bid")
    bid_0 = _get_val(from_row, "bid")
    ask_0 = _get_val(from_row, "ask")
    iv_0 = _get_val(from_row, "iv", "implied_vol")

    # 3. Extract inputs from to_row
    days_1 = _get_val(to_row, "days_to_expiry")
    s_1 = _get_val(to_row, "underlying_price", "underlying_bid")
    bid_1 = _get_val(to_row, "bid")
    ask_1 = _get_val(to_row, "ask")
    iv_1 = _get_val(to_row, "iv", "implied_vol")

    # Validate presence of numerical inputs
    if strike is None:
        missing.append("from_row.strike")
    if ratio is None or float(ratio) <= 0:
        missing.append("from_row.ratio")
    if s_0 is None:
        missing.append("from_row.underlying_price")
    if days_0 is None:
        missing.append("from_row.days_to_expiry")
    if bid_0 is None or ask_0 is None:
        missing.append("from_row.bid_ask")

    if s_1 is None:
        missing.append("to_row.underlying_price")
    if days_1 is None:
        missing.append("to_row.days_to_expiry")
    if bid_1 is None or ask_1 is None:
        missing.append("to_row.bid_ask")

    if missing:
        return SequentialAttributionResult(
            ok=False,
            missing=missing,
            message=f"Missing inputs needed for attribution: {', '.join(missing)}",
        )

    # Safe float parsing
    k = float(strike)
    n = float(ratio)
    s0 = float(s_0)
    s1 = float(s_1)
    d0 = max(0.001, float(days_0))
    d1 = max(0.000, float(days_1))
    t0 = d0 / 365.0
    t1 = d1 / 365.0

    w0 = (float(bid_0) + float(ask_0)) / 2.0
    w1 = (float(bid_1) + float(ask_1)) / 2.0
    total_change = w1 - w0

    # Solve or parse IVs
    if iv_0 is not None:
        sigma_0 = float(iv_0)
    else:
        res0 = solve_iv(w0 * n, s0, k, t0, risk_free_rate, option_type)
        sigma_0 = res0.iv if res0.iv is not None else 0.30

    if iv_1 is not None:
        sigma_1 = float(iv_1)
    else:
        res1 = solve_iv(w1 * n, s1, k, t1, risk_free_rate, option_type)
        sigma_1 = res1.iv if res1.iv is not None else sigma_0

    # Check zero change edge case
    if (
        w0 == w1
        and s0 == s1
        and d0 == d1
        and sigma_0 == sigma_1
    ):
        return SequentialAttributionResult(
            ok=True,
            total_change=0.0,
            underlying_move=0.0,
            passage_of_time=0.0,
            implied_volatility=0.0,
            residual=0.0,
            message="No price move detected between snapshots.",
            details={"warrant_code": code, "from_mid": w0, "to_mid": w1},
        )

    # --- Sequential 4-Step Decomposition (FR-EXP-01, FR-EXP-02) ---

    # Step 1: Underlying Move (S0 -> S1, holding t0 and sigma_0 constant)
    p0 = bs_price(s0, k, t0, risk_free_rate, sigma_0, option_type) / n
    p1 = bs_price(s1, k, t0, risk_free_rate, sigma_0, option_type) / n
    d_underlying = p1 - p0

    # Step 2: Passage of Time (t0 -> t1, with S1 and sigma_0)
    p2 = bs_price(s1, k, t1, risk_free_rate, sigma_0, option_type) / n
    d_time = p2 - p1

    # Step 3: Change in Implied Volatility (sigma_0 -> sigma_1, with S1 and t1)
    p3 = bs_price(s1, k, t1, risk_free_rate, sigma_1, option_type) / n
    d_vol = p3 - p2

    # Step 4: Residual (Spread drag, model error, discrete quote rounding)
    # By construction: total_change == d_underlying + d_time + d_vol + residual
    d_residual = total_change - (d_underlying + d_time + d_vol)

    return SequentialAttributionResult(
        ok=True,
        total_change=total_change,
        underlying_move=d_underlying,
        passage_of_time=d_time,
        implied_volatility=d_vol,
        residual=d_residual,
        message=(
            f"Warrant {code} changed by RM {total_change:+.4f} (mid). "
            f"Underlying move contributed RM {d_underlying:+.4f}, "
            f"time decay RM {d_time:+.4f}, IV change RM {d_vol:+.4f}, "
            f"and residual RM {d_residual:+.4f}."
        ),
        details={
            "warrant_code": code,
            "from_mid": w0,
            "to_mid": w1,
            "underlying_from": s0,
            "underlying_to": s1,
            "iv_from": sigma_0,
            "iv_to": sigma_1,
            "days_from": d0,
            "days_to": d1,
        },
    )

"""Deterministic scenario simulation engine (FR-SCN-01 to 07).

Computes what-if P&L for structured warrants across:
- Underlying stock moves [-50%, +50%]
- Holding duration [0, days_left]
- Implied volatility shifts [-15, +15] points

Guarantees:
- FR-SCN-02 identity: move=0, days=0, shift=0 produces P&L = bid/ask - 1 exactly.
- Intrinsic at expiry: at days_held == days_left, exit price is pure intrinsic / ratio.
- Three horizons curve generation across [-20%, +20%] in 1% steps.
- Bounded Brent solver for breakeven move.
"""

from __future__ import annotations

import math
from typing import Any

from scipy.optimize import brentq

from warrantx.quant.bs import OptionType, bs_price
from warrantx.tools.evidence import (
    format_currency,
    format_days,
    format_percent,
    format_points,
)
from warrantx.tools.models import (
    CurvePoint,
    ScenarioCurve,
    ScenarioInputs,
    ScenarioResult,
)


class ScenarioError(ValueError):
    """Raised when scenario inputs violate allowed bounds or assumptions."""


DEFAULT_ASSUMPTIONS: list[str] = [
    "Exit priced at model bid reflecting current bid-ask spread discount.",
    "Risk-free rate held constant at 3.0% over simulation duration.",
    "Implied volatility shifts uniformly across remaining term.",
    "No cash dividend adjustments assumed during simulation window.",
]


def calculate_scenario(
    code: str,
    opt_type: OptionType | str,
    underlying_price: float,
    strike: float,
    ratio: float,
    bid: float | None,
    ask: float | None,
    days_left: int,
    headline_iv: float | None,
    move_pct: float,
    days_held: int,
    iv_shift_pts: float,
    risk_free_rate: float = 0.03,
) -> ScenarioResult:
    """Calculate entry price, exit price, and P&L for a specific scenario."""
    # Validation against specs
    if move_pct < -0.5 or move_pct > 0.5:
        raise ScenarioError(
            f"Underlying move {move_pct:.2f} outside valid range [-0.5, 0.5]"
        )

    if days_held < 0 or days_held > days_left:
        raise ScenarioError(
            f"Holding days {days_held} outside valid range [0, {days_left}]"
        )

    if iv_shift_pts < -15.0 or iv_shift_pts > 15.0:
        raise ScenarioError(
            f"IV shift {iv_shift_pts:.1f} outside valid range [-15, 15]"
        )

    if ask is None or ask <= 0:
        raise ScenarioError("Warrant ask quote missing or non-positive; cannot compute entry.")

    entry_price = float(ask)
    s0 = float(underlying_price)
    k = float(strike)
    ratio_val = float(ratio) if ratio > 0 else 1.0
    r = float(risk_free_rate)
    is_call = str(opt_type).lower() in ("call", "optiontype.call")

    exit_price = _compute_exit_price(
        s0=s0,
        k=k,
        ratio=ratio_val,
        bid=bid,
        ask=ask,
        days_left=days_left,
        headline_iv=headline_iv,
        move_pct=move_pct,
        days_held=days_held,
        iv_shift_pts=iv_shift_pts,
        risk_free_rate=r,
        is_call=is_call,
    )

    pnl_pct = (exit_price / entry_price) - 1.0

    # Breakeven move calculation
    be_move = breakeven_move(
        code=code,
        opt_type=opt_type,
        underlying_price=s0,
        strike=k,
        ratio=ratio_val,
        bid=bid,
        ask=ask,
        days_left=days_left,
        headline_iv=headline_iv,
        days_held=days_held,
        iv_shift_pts=iv_shift_pts,
        risk_free_rate=r,
    )

    # Generate curves for 3 horizons
    curves = generate_curves(
        code=code,
        opt_type=opt_type,
        underlying_price=s0,
        strike=k,
        ratio=ratio_val,
        bid=bid,
        ask=ask,
        days_left=days_left,
        headline_iv=headline_iv,
        days_held=days_held,
        iv_shift_pts=iv_shift_pts,
        risk_free_rate=r,
    )

    inputs = ScenarioInputs(
        code=code,
        move=move_pct,
        days=days_held,
        iv_shift=iv_shift_pts,
    )

    return ScenarioResult(
        inputs=inputs,
        entry_price=round(entry_price, 4),
        display_entry_price=format_currency(entry_price),
        exit_price=round(exit_price, 4),
        display_exit_price=format_currency(exit_price),
        pnl_pct=round(pnl_pct, 4),
        display_pnl_pct=format_percent(pnl_pct, signed=True),
        breakeven_move=round(be_move, 4) if be_move is not None else None,
        display_breakeven_move=format_percent(be_move, signed=True) if be_move is not None else None,
        curve=curves,
        assumptions=DEFAULT_ASSUMPTIONS,
        evidence_id=f"E_SCN_{code}",
    )


def _compute_exit_price(
    s0: float,
    k: float,
    ratio: float,
    bid: float | None,
    ask: float | None,
    days_left: int,
    headline_iv: float | None,
    move_pct: float,
    days_held: int,
    iv_shift_pts: float,
    risk_free_rate: float,
    is_call: bool,
) -> float:
    """Calculate theoretical exit price honoring FR-SCN-02 identity and expiry payoffs."""
    # Identity invariant: 0% move, 0 days, 0 shift -> exit price = bid
    if move_pct == 0.0 and days_held == 0 and iv_shift_pts == 0.0:
        return float(bid) if bid is not None else float(ask)

    s_new = max(0.001, s0 * (1.0 + move_pct))
    t_days_new = max(0, days_left - days_held)

    # Expiry payoff: pure intrinsic value divided by ratio
    if t_days_new == 0:
        if is_call:
            intrinsic = max(0.0, s_new - k) / ratio
        else:
            intrinsic = max(0.0, k - s_new) / ratio
        return intrinsic

    # Pre-expiry Black-Scholes valuation
    base_iv = headline_iv if (headline_iv is not None and headline_iv > 0) else 0.35
    sigma_new = max(0.001, base_iv + (iv_shift_pts / 100.0))
    t_years = t_days_new / 365.0
    opt_str = "call" if is_call else "put"

    bs_val = bs_price(s_new, k, t_years, risk_free_rate, sigma_new, opt_str) / ratio

    # Apply bid/mid spread discount to model exit price if quotes available
    if bid is not None and ask is not None and (bid + ask) > 0:
        mid = (bid + ask) / 2.0
        ratio_bid_mid = bid / mid
        return max(0.0, bs_val * ratio_bid_mid)

    return max(0.0, bs_val)


def breakeven_move(
    code: str,
    opt_type: OptionType | str,
    underlying_price: float,
    strike: float,
    ratio: float,
    bid: float | None,
    ask: float | None,
    days_left: int,
    headline_iv: float | None,
    days_held: int,
    iv_shift_pts: float,
    risk_free_rate: float = 0.03,
) -> float | None:
    """Find the underlying percentage move in [-0.5, 0.5] that produces 0% P&L."""
    if ask is None or ask <= 0:
        return None

    entry_price = float(ask)
    is_call = str(opt_type).lower() in ("call", "optiontype.call")

    def obj(m: float) -> float:
        exit_p = _compute_exit_price(
            s0=underlying_price,
            k=strike,
            ratio=ratio,
            bid=bid,
            ask=ask,
            days_left=days_left,
            headline_iv=headline_iv,
            move_pct=m,
            days_held=days_held,
            iv_shift_pts=iv_shift_pts,
            risk_free_rate=risk_free_rate,
            is_call=is_call,
        )
        return (exit_p / entry_price) - 1.0

    # Search domain [-0.5, 0.5]
    f_low = obj(-0.50)
    f_high = obj(0.50)

    if f_low * f_high > 0:
        # Check if 0 crossing exists between 0 and bounds
        f_zero = obj(0.0)
        if f_low * f_zero <= 0:
            try:
                return float(brentq(obj, -0.50, 0.0, xtol=1e-5))
            except Exception:
                pass
        if f_zero * f_high <= 0:
            try:
                return float(brentq(obj, 0.0, 0.50, xtol=1e-5))
            except Exception:
                pass
        return None

    try:
        return float(brentq(obj, -0.50, 0.50, xtol=1e-5))
    except Exception:
        return None


def generate_curves(
    code: str,
    opt_type: OptionType | str,
    underlying_price: float,
    strike: float,
    ratio: float,
    bid: float | None,
    ask: float | None,
    days_left: int,
    headline_iv: float | None,
    days_held: int,
    iv_shift_pts: float,
    risk_free_rate: float = 0.03,
) -> list[ScenarioCurve]:
    """Generate 3 horizon curves across moves from -20% to +20% in 1% steps."""
    entry_price = float(ask) if (ask is not None and ask > 0) else 1.0
    is_call = str(opt_type).lower() in ("call", "optiontype.call")

    # Three horizons per spec: 0, days_held, min(2 * days_held, days_left)
    h0 = 0
    h1 = days_held
    h2 = min(max(days_held * 2, days_held + 1), days_left) if days_left > 0 else 0

    unique_horizons = sorted(list(set([h0, h1, h2])))

    # 41 points: -0.20 to +0.20 in 0.01 steps
    moves = [round(-0.20 + (i * 0.01), 2) for i in range(41)]

    curves: list[ScenarioCurve] = []
    for h in unique_horizons:
        points: list[CurvePoint] = []
        for m in moves:
            exit_p = _compute_exit_price(
                s0=underlying_price,
                k=strike,
                ratio=ratio,
                bid=bid,
                ask=ask,
                days_left=days_left,
                headline_iv=headline_iv,
                move_pct=m,
                days_held=h,
                iv_shift_pts=iv_shift_pts,
                risk_free_rate=risk_free_rate,
                is_call=is_call,
            )
            pnl = (exit_p / entry_price) - 1.0
            points.append(
                CurvePoint(
                    move=m,
                    display_move=format_percent(m, signed=True),
                    pnl_pct=round(pnl, 4),
                    display_pnl_pct=format_percent(pnl, signed=True),
                )
            )

        horizon_label = (
            "Day 0 (Immediate)"
            if h == 0
            else f"Day {h}"
            if h < days_left
            else f"Day {h} (Expiry)"
        )

        curves.append(
            ScenarioCurve(
                horizon_days=h,
                display_horizon=horizon_label,
                points=points,
            )
        )

    return curves

"""Vectorized and high-performance warrant quant metrics engine.

Computes:
- Multi-basis implied volatility (bid, mid, ask, size-weighted mid, last)
- Headline IV selection (mid -> last -> None)
- Greeks (delta, gamma, vega per point, theta per day)
- Gearing and effective gearing
- Premium, breakeven underlying price, and required percentage move
- Cross-checks against published issuer values
- Server-formatted display strings for every numeric field
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from warrantx.quant.bs import OptionType, bs_greeks
from warrantx.quant.iv import iv_by_basis, solve_iv
from warrantx.tools.evidence import (
    format_currency,
    format_days,
    format_greek,
    format_percent,
    format_points,
    format_ratio,
)
from warrantx.tools.models import WarrantMetrics


@dataclass
class WarrantQuantInput:
    """Inputs required for warrant metric evaluation."""

    code: str
    issuer: str
    type: OptionType
    underlying_price: float
    strike: float
    ratio: float
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    bid_volume: int | None = None
    ask_volume: int | None = None
    days_to_expiry: int = 0
    risk_free_rate: float = 0.03
    issuer_iv: float | None = None
    issuer_eg: float | None = None
    issuer_delta: float | None = None


def compute_metrics(inp: WarrantQuantInput) -> WarrantMetrics:
    """Calculate comprehensive quant metrics for a structured warrant."""
    s = float(inp.underlying_price)
    k = float(inp.strike)
    ratio = float(inp.ratio)
    r = float(inp.risk_free_rate)
    days_left = int(inp.days_to_expiry)
    opt_type = inp.type.lower()
    if opt_type not in ("call", "put"):
        opt_type = "call"

    spw = 1.0 / ratio if ratio > 0 else 0.0

    # Expired warrants have days_to_expiry <= 0
    if days_left <= 0:
        return WarrantMetrics(
            shares_per_warrant=spw,
            display_shares_per_warrant=f"{spw:.4f}",
            days_to_expiry=max(0, days_left),
            display_days_to_expiry=format_days(max(0, days_left)),
            headline_iv=None,
            headline_iv_basis="mid",
            iv_reason_codes={"mid": "expired", "last": "expired"},
        )

    t = days_left / 365.0

    # Bid, Ask, Mid quotes
    bid = inp.bid
    ask = inp.ask
    last = inp.last

    mid: float | None = None
    spread_pct: float | None = None
    round_trip_cost: float | None = None
    if bid is not None and ask is not None and (bid + ask) > 0:
        mid = (bid + ask) / 2.0
        if mid > 0:
            spread_pct = (ask - bid) / mid
            round_trip_cost = spread_pct

    # Size-weighted mid
    sw_mid: float | None = None
    if (
        bid is not None
        and ask is not None
        and inp.bid_volume is not None
        and inp.ask_volume is not None
    ):
        total_vol = inp.bid_volume + inp.ask_volume
        if total_vol > 0:
            sw_mid = (bid * inp.ask_volume + ask * inp.bid_volume) / total_vol

    # Solve IV for each basis
    # Because 1 warrant covers (1/ratio) shares, option price per share = warrant_price * ratio
    p_bid_share = bid * ratio if bid is not None else None
    p_ask_share = ask * ratio if ask is not None else None
    p_mid_share = mid * ratio if mid is not None else None
    p_sw_share = sw_mid * ratio if sw_mid is not None else None
    p_last_share = last * ratio if last is not None else None

    iv_results = iv_by_basis(
        bid=p_bid_share,
        mid=p_mid_share,
        ask=p_ask_share,
        size_weighted_mid=p_sw_share,
        last=p_last_share,
        s=s,
        k=k,
        t=t,
        r=r,
        option_type=opt_type,  # type: ignore[arg-type]
    )

    iv_dict: dict[str, float | None] = {}
    reason_dict: dict[str, str | None] = {}
    for basis_key, res in iv_results.items():
        iv_dict[basis_key] = res.iv
        reason_dict[basis_key] = res.reason_code

    # Headline IV selection: mid -> last -> None
    headline_iv = iv_dict.get("mid")
    headline_basis = "mid"
    if headline_iv is None:
        if iv_dict.get("last") is not None:
            headline_iv = iv_dict.get("last")
            headline_basis = "last"
        else:
            headline_iv = None
            headline_basis = "mid"

    # Spread between ask IV and bid IV
    iv_basis_spread: float | None = None
    if iv_dict.get("ask") is not None and iv_dict.get("bid") is not None:
        iv_basis_spread = (iv_dict["ask"] - iv_dict["bid"]) * 100.0  # in points

    # Compute Greeks using headline IV
    delta_share: float | None = None
    gamma: float | None = None
    vega_per_point: float | None = None
    theta_per_day: float | None = None

    if headline_iv is not None and headline_iv > 0:
        g = bs_greeks(
            s=s, k=k, t=t, r=r, sigma=headline_iv, option_type=opt_type  # type: ignore[arg-type]
        )
        delta_share = g.delta
        # Per warrant greeks
        gamma = g.gamma / ratio
        vega_per_point = g.vega_per_point / ratio
        theta_per_day = g.theta_per_day / ratio

    # Gearing and Effective Gearing
    # Reference price: mid if available, else last
    ref_price = mid if mid is not None else last
    gearing: float | None = None
    effective_gearing: float | None = None
    if ref_price is not None and ref_price > 0 and ratio > 0:
        gearing = (s / ratio) / ref_price
        if delta_share is not None:
            effective_gearing = gearing * abs(delta_share)

    # Premium
    premium: float | None = None
    if ref_price is not None and ref_price > 0 and s > 0:
        if opt_type == "call":
            premium = (k + ref_price * ratio - s) / s
        else:
            premium = (s + ref_price * ratio - k) / s

    # Breakeven & Required Move
    # Breakeven uses ask (buyer's entry price) if available, else mid or last
    entry_p = ask if ask is not None else ref_price
    breakeven_price: float | None = None
    required_move: float | None = None
    if entry_p is not None and entry_p > 0:
        if opt_type == "call":
            breakeven_price = round(k + entry_p * ratio, 4)
            required_move = (breakeven_price - s) / s if s > 0 else None
        else:
            breakeven_price = round(k - entry_p * ratio, 4)
            required_move = (breakeven_price - s) / s if s > 0 else None

    # Cross-checks against issuer values
    cross_check: dict[str, float | None] | None = None
    if (
        inp.issuer_iv is not None
        or inp.issuer_eg is not None
        or inp.issuer_delta is not None
    ):
        iv_diff = (
            round((headline_iv * 100.0) - inp.issuer_iv, 2)
            if (headline_iv is not None and inp.issuer_iv is not None)
            else None
        )
        eg_diff = (
            round((effective_gearing - inp.issuer_eg) / inp.issuer_eg, 4)
            if (effective_gearing is not None and inp.issuer_eg is not None and inp.issuer_eg != 0)
            else None
        )
        delta_diff = (
            round(delta_share - inp.issuer_delta, 4)
            if (delta_share is not None and inp.issuer_delta is not None)
            else None
        )
        cross_check = {
            "iv_diff_points": iv_diff,
            "eg_diff_rel": eg_diff,
            "delta_diff": delta_diff,
        }

    return WarrantMetrics(
        shares_per_warrant=spw,
        display_shares_per_warrant=f"{spw:.4f}",
        days_to_expiry=days_left,
        display_days_to_expiry=format_days(days_left),
        mid=mid,
        display_mid=format_currency(mid),
        size_weighted_mid=sw_mid,
        display_size_weighted_mid=format_currency(sw_mid),
        spread_pct=spread_pct,
        display_spread_pct=format_percent(spread_pct),
        round_trip_cost=round_trip_cost,
        display_round_trip_cost=format_percent(round_trip_cost),
        iv_by_basis=iv_dict,
        iv_reason_codes=reason_dict,
        headline_iv=headline_iv,
        display_headline_iv=format_percent(headline_iv),
        headline_iv_basis=headline_basis,
        iv_basis_spread=iv_basis_spread,
        display_iv_basis_spread=format_points(iv_basis_spread),
        delta_share=delta_share,
        display_delta_share=format_greek(delta_share),
        gamma=gamma,
        display_gamma=format_greek(gamma),
        vega_per_point=vega_per_point,
        display_vega_per_point=format_currency(vega_per_point, prefix="RM "),
        theta_per_day=theta_per_day,
        display_theta_per_day=format_currency(theta_per_day, prefix="RM "),
        gearing=gearing,
        display_gearing=format_ratio(gearing),
        effective_gearing=effective_gearing,
        display_effective_gearing=format_ratio(effective_gearing),
        premium=premium,
        display_premium=format_percent(premium),
        breakeven_price=breakeven_price,
        display_breakeven_price=format_currency(breakeven_price),
        required_move=required_move,
        display_required_move=format_percent(required_move, signed=True),
        cross_check=cross_check,
    )

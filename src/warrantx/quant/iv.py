"""Brent implied volatility solver and multi-basis evaluator.

Pure functions wrapping SciPy's brentq root finder with strict no-arbitrage boundary
enforcement and standardized failure reason codes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal
from scipy.optimize import brentq

from warrantx.quant.bs import OptionType, bs_price, check_arbitrage_bounds

IVReasonCode = Literal[
    "no_quote",
    "non_positive_price",
    "below_intrinsic",
    "above_upper_bound",
    "expired",
    "solver_failed",
    "non_finite",
]


@dataclass(frozen=True)
class IVResult:
    """Implied volatility calculation outcome."""

    iv: float | None
    reason_code: IVReasonCode | None = None


def solve_iv(
    price: float | None,
    s: float,
    k: float,
    t: float,
    r: float,
    option_type: OptionType = "call",
) -> IVResult:
    """Solve for implied volatility using Brent's method.

    Returns an IVResult with float IV on success, or None with a machine-readable reason code.
    """
    if price is None:
        return IVResult(iv=None, reason_code="no_quote")

    if price <= 0.0:
        return IVResult(iv=None, reason_code="non_positive_price")

    if t <= 0.0:
        return IVResult(iv=None, reason_code="expired")

    if s <= 0.0 or k <= 0.0:
        return IVResult(iv=None, reason_code="solver_failed")

    lower_bound, upper_bound = check_arbitrage_bounds(s=s, k=k, t=t, r=r, option_type=option_type)

    if price < lower_bound - 1e-6:
        return IVResult(iv=None, reason_code="below_intrinsic")

    if price > upper_bound + 1e-6:
        return IVResult(iv=None, reason_code="above_upper_bound")

    # If price is virtually at lower bound (intrinsic)
    if abs(price - lower_bound) < 1e-6:
        return IVResult(iv=0.001, reason_code=None)

    def objective(sigma: float) -> float:
        return bs_price(s=s, k=k, t=t, r=r, sigma=sigma, option_type=option_type) - price

    a = 0.0001
    b = 5.0000

    fa = objective(a)
    fb = objective(b)

    if fa * fb > 0:
        # Try wider bracket up to 10.0 (1000% vol)
        b = 10.0
        fb = objective(b)
        if fa * fb > 0:
            return IVResult(iv=None, reason_code="solver_failed")

    try:
        root = brentq(objective, a, b, xtol=1e-5, rtol=1e-5, maxiter=100)
        if math.isnan(root) or math.isinf(root):
            return IVResult(iv=None, reason_code="non_finite")
        return IVResult(iv=float(root), reason_code=None)
    except Exception:
        return IVResult(iv=None, reason_code="solver_failed")


def iv_by_basis(
    bid: float | None,
    mid: float | None,
    ask: float | None,
    size_weighted_mid: float | None,
    last: float | None,
    s: float,
    k: float,
    t: float,
    r: float,
    option_type: OptionType = "call",
) -> dict[str, IVResult]:
    """Calculate implied volatility across all standard pricing bases."""
    bases: dict[str, float | None] = {
        "bid": bid,
        "mid": mid,
        "ask": ask,
        "size_weighted_mid": size_weighted_mid,
        "last": last,
    }

    results: dict[str, IVResult] = {}
    for basis_name, p in bases.items():
        results[basis_name] = solve_iv(
            price=p, s=s, k=k, t=t, r=r, option_type=option_type
        )

    return results

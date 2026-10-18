"""Black-Scholes pricing, analytical Greeks, and no-arbitrage bounds.

Pure functions implemented with SciPy and NumPy. Deterministic, floating-point safe,
free of side effects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

OptionType = Literal["call", "put"]

# Fast C-level normal CDF and PDF using Python's built-in math module
_INV_SQRT_2 = 0.70710678118654752440
_INV_SQRT_2PI = 0.39894228040143267794


def _std_norm_cdf(x: float) -> float:
    """Fast standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x * _INV_SQRT_2))


def _std_norm_pdf(x: float) -> float:
    """Fast standard normal probability density function."""
    return _INV_SQRT_2PI * math.exp(-0.5 * x * x)


@dataclass(frozen=True)
class Greeks:
    """Option Greeks container."""

    delta: float
    gamma: float
    vega_per_point: float  # Price change per +1 percentage point (+0.01) in IV
    theta_per_day: float   # Price decay per 1 calendar day (T - 1/365)


def check_arbitrage_bounds(
    s: float, k: float, t: float, r: float, option_type: OptionType = "call"
) -> tuple[float, float]:
    """Calculate the theoretical no-arbitrage lower and upper bounds for an option price.

    Call bounds: max(0.0, S - K * exp(-r * T)) <= C <= S
    Put bounds:  max(0.0, K * exp(-r * T) - S) <= P <= K * exp(-r * T)
    """
    if t <= 0.0:
        if option_type == "call":
            intrinsic = max(0.0, s - k)
            return intrinsic, intrinsic
        else:
            intrinsic = max(0.0, k - s)
            return intrinsic, intrinsic

    discounted_k = k * math.exp(-r * t)
    if option_type == "call":
        lower = max(0.0, s - discounted_k)
        upper = s
    else:
        lower = max(0.0, discounted_k - s)
        upper = discounted_k

    return lower, upper


def bs_price(
    s: float,
    k: float,
    t: float,
    r: float,
    sigma: float,
    option_type: OptionType = "call",
) -> float:
    """Calculate Black-Scholes European option price.

    Parameters:
    - s: Underlying asset price
    - k: Strike price
    - t: Time to maturity in years
    - r: Annualized risk-free interest rate
    - sigma: Annualized volatility (e.g. 0.35 for 35%)
    - option_type: "call" or "put"
    """
    if s <= 0.0 or k <= 0.0 or sigma <= 0.0:
        return 0.0

    if t <= 0.0:
        return max(0.0, s - k) if option_type == "call" else max(0.0, k - s)

    sqrt_t = math.sqrt(t)
    sigma_sqrt_t = sigma * sqrt_t
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t

    discount = math.exp(-r * t)
    if option_type == "call":
        price = s * _std_norm_cdf(d1) - k * discount * _std_norm_cdf(d2)
    else:
        price = k * discount * _std_norm_cdf(-d2) - s * _std_norm_cdf(-d1)

    return float(max(0.0, price))


def bs_greeks(
    s: float,
    k: float,
    t: float,
    r: float,
    sigma: float,
    option_type: OptionType = "call",
) -> Greeks:
    """Calculate Black-Scholes analytical Greeks."""
    if s <= 0.0 or k <= 0.0 or sigma <= 0.0 or t <= 0.0:
        return Greeks(
            delta=0.0,
            gamma=0.0,
            vega_per_point=0.0,
            theta_per_day=0.0,
        )

    sqrt_t = math.sqrt(t)
    sigma_sqrt_t = sigma * sqrt_t
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t

    pdf_d1 = _std_norm_pdf(d1)
    discount = math.exp(-r * t)

    # Gamma is identical for call and put
    gamma = pdf_d1 / (s * sigma_sqrt_t)

    # Vega (total) is identical for call and put: S * sqrt(T) * pdf(d1)
    # Vega per 1 percentage point (+0.01 shift in volatility):
    vega_per_point = (s * sqrt_t * pdf_d1) / 100.0

    if option_type == "call":
        delta = float(_std_norm_cdf(d1))
        # Theta per year
        theta_annual = -(s * pdf_d1 * sigma) / (2.0 * sqrt_t) - r * k * discount * _std_norm_cdf(d2)
    else:
        delta = float(_std_norm_cdf(d1) - 1.0)
        # Theta per year
        theta_annual = -(s * pdf_d1 * sigma) / (2.0 * sqrt_t) + r * k * discount * _std_norm_cdf(-d2)

    # Per calendar day (365 days / year standard in options markets)
    theta_per_day = theta_annual / 365.0

    return Greeks(
        delta=delta,
        gamma=float(gamma),
        vega_per_point=float(vega_per_point),
        theta_per_day=float(theta_per_day),
    )


def black_scholes(
    s: float,
    k: float,
    t: float,
    r: float,
    sigma: float,
    option_type: OptionType = "call",
) -> tuple[float, Greeks]:
    """Compute price and all Greeks in a single pass."""
    price = bs_price(s=s, k=k, t=t, r=r, sigma=sigma, option_type=option_type)
    greeks = bs_greeks(s=s, k=k, t=t, r=r, sigma=sigma, option_type=option_type)
    return price, greeks

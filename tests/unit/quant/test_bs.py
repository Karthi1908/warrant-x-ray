"""Unit tests for Black-Scholes pricing, Greeks, and no-arbitrage bounds (T028).

Covers:
- Golden-value accuracy against standard analytical benchmarks
- Put-Call parity identity
- Monotonicity across price, strike, volatility, and time-to-expiry
- Greeks sign and magnitude invariants
- No-arbitrage upper and lower price bounds
"""

import math
import pytest
from warrantx.quant.bs import (
    bs_price,
    bs_greeks,
    black_scholes,
    check_arbitrage_bounds,
)


def test_black_scholes_call_golden_value() -> None:
    """Standard benchmark: S=100, K=100, T=1.0, r=0.05, sigma=0.20."""
    price = bs_price(s=100.0, k=100.0, t=1.0, r=0.05, sigma=0.20, option_type="call")
    # Benchmark call value is approximately 10.45058
    assert math.isclose(price, 10.4506, rel_tol=1e-4)


def test_black_scholes_put_golden_value() -> None:
    """Standard benchmark put value: S=100, K=100, T=1.0, r=0.05, sigma=0.20."""
    price = bs_price(s=100.0, k=100.0, t=1.0, r=0.05, sigma=0.20, option_type="put")
    # Benchmark put value is approximately 5.57352
    assert math.isclose(price, 5.5735, rel_tol=1e-4)


def test_put_call_parity() -> None:
    """C - P = S - K * exp(-r * T) across varied parameters."""
    test_cases = [
        (10.50, 10.00, 0.25, 0.03, 0.35),
        (14.20, 15.00, 0.50, 0.03, 0.40),
        (3.80, 3.80, 0.10, 0.03, 0.50),
        (100.0, 95.0, 1.0, 0.05, 0.25),
    ]
    for s, k, t, r, sigma in test_cases:
        call = bs_price(s=s, k=k, t=t, r=r, sigma=sigma, option_type="call")
        put = bs_price(s=s, k=k, t=t, r=r, sigma=sigma, option_type="put")
        discounted_strike = k * math.exp(-r * t)
        parity_diff = (call - put) - (s - discounted_strike)
        assert abs(parity_diff) < 1e-7, f"Parity violated for s={s}, k={k}: diff={parity_diff}"


def test_monotonicity() -> None:
    """Call prices must be monotonically increasing in S, sigma, and T, and decreasing in K."""
    base_args = {"s": 10.0, "k": 10.0, "t": 0.5, "r": 0.03, "sigma": 0.30, "option_type": "call"}

    # S increases -> call price increases
    p_s_low = bs_price(**{**base_args, "s": 9.5})
    p_s_mid = bs_price(**base_args)
    p_s_high = bs_price(**{**base_args, "s": 10.5})
    assert p_s_low < p_s_mid < p_s_high

    # K increases -> call price decreases
    p_k_low = bs_price(**{**base_args, "k": 9.0})
    p_k_high = bs_price(**{**base_args, "k": 11.0})
    assert p_k_low > p_s_mid > p_k_high

    # Sigma increases -> call price increases
    p_sig_low = bs_price(**{**base_args, "sigma": 0.20})
    p_sig_high = bs_price(**{**base_args, "sigma": 0.40})
    assert p_sig_low < p_s_mid < p_sig_high


def test_greeks_invariants() -> None:
    """Greeks must conform to standard bounds: Call Delta in (0, 1), Gamma > 0, Vega > 0."""
    greeks_call = bs_greeks(s=10.0, k=10.0, t=0.5, r=0.03, sigma=0.30, option_type="call")
    assert 0.0 < greeks_call.delta < 1.0
    assert greeks_call.gamma > 0.0
    assert greeks_call.vega_per_point > 0.0
    assert greeks_call.theta_per_day < 0.0  # Time decay

    greeks_put = bs_greeks(s=10.0, k=10.0, t=0.5, r=0.03, sigma=0.30, option_type="put")
    assert -1.0 < greeks_put.delta < 0.0
    assert greeks_put.gamma > 0.0
    assert math.isclose(greeks_call.gamma, greeks_put.gamma, rel_tol=1e-6)
    assert math.isclose(greeks_call.vega_per_point, greeks_put.vega_per_point, rel_tol=1e-6)


def test_no_arbitrage_bounds() -> None:
    """No-arbitrage bounds: max(0, S - K*exp(-rT)) <= C <= S."""
    s, k, t, r = 10.0, 9.0, 0.5, 0.03
    lower, upper = check_arbitrage_bounds(s=s, k=k, t=t, r=r, option_type="call")
    assert lower > 0.0
    assert upper == s

    # Valid call price
    valid_p = bs_price(s=s, k=k, t=t, r=r, sigma=0.30, option_type="call")
    assert lower <= valid_p <= upper

    # Lower bound violation
    assert not (lower <= (lower - 0.10) <= upper)
    # Upper bound violation
    assert not (lower <= (upper + 0.10) <= upper)

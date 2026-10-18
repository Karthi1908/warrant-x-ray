"""Hypothesis property-based tests and performance benchmarks (T033).

Covers:
- Robustness: random inputs within valid mathematical ranges never crash or produce NaN
- Performance benchmark: 300 warrants with 5 IV bases evaluated in < 1.0 s on 1 core (SC-010)
"""

import time
import math
import pytest
from hypothesis import given, settings, strategies as st
from warrantx.quant.bs import bs_price, bs_greeks
from warrantx.quant.metrics import compute_metrics, WarrantQuantInput


@settings(max_examples=50, deadline=None)
@given(
    s=st.floats(min_value=0.5, max_value=500.0),
    k=st.floats(min_value=0.5, max_value=500.0),
    t=st.floats(min_value=0.01, max_value=5.0),
    r=st.floats(min_value=0.0, max_value=0.15),
    sigma=st.floats(min_value=0.05, max_value=2.0),
    opt_type=st.sampled_from(["call", "put"]),
)
def test_black_scholes_property_no_nan(
    s: float, k: float, t: float, r: float, sigma: float, opt_type: str
) -> None:
    """Black-Scholes price and Greeks must always be finite and non-NaN."""
    price = bs_price(s=s, k=k, t=t, r=r, sigma=sigma, option_type=opt_type)
    assert not math.isnan(price)
    assert not math.isinf(price)
    assert price >= 0.0

    greeks = bs_greeks(s=s, k=k, t=t, r=r, sigma=sigma, option_type=opt_type)
    assert not math.isnan(greeks.delta)
    assert not math.isnan(greeks.gamma)
    assert not math.isnan(greeks.vega_per_point)
    assert not math.isnan(greeks.theta_per_day)


def test_performance_benchmark_300_warrants() -> None:
    """300 warrants evaluated with 5 IV bases must complete in < 1.0 second on 1 core."""
    inputs = [
        WarrantQuantInput(
            code=f"W{i:04d}",
            issuer="CGS",
            type="call" if i % 2 == 0 else "put",
            underlying_price=10.0 + (i % 20) * 0.25,
            strike=10.0 + ((i + 5) % 20) * 0.25,
            ratio=4.0,
            bid=0.080 + (i % 10) * 0.005,
            ask=0.090 + (i % 10) * 0.005,
            last=0.085 + (i % 10) * 0.005,
            bid_volume=10000 + i * 100,
            ask_volume=20000 + i * 100,
            days_to_expiry=30 + (i % 180),
            risk_free_rate=0.03,
        )
        for i in range(300)
    ]

    start_time = time.perf_counter()
    results = [compute_metrics(inp) for inp in inputs]
    elapsed = time.perf_counter() - start_time

    assert len(results) == 300
    print(f"Computed 300 warrants in {elapsed:.3f} seconds.")
    # Benchmark budget per SC-010: < 1.0 s
    assert elapsed < 1.0, f"Benchmark failed: took {elapsed:.3f} s (budget: 1.0 s)"

"""Unit tests for Brent implied volatility solver and iv_by_basis (T029).

Covers:
- Round-trip recovery across a wide IV grid (5% to 200%)
- Proper error reason codes when price violates no-arbitrage bounds
- Non-positive prices, missing quotes, expired options
- Multi-basis inversion (bid, mid, ask, size-weighted mid, last)
"""

import math
import pytest
from warrantx.quant.bs import bs_price
from warrantx.quant.iv import (
    solve_iv,
    iv_by_basis,
    IVResult,
)


def test_iv_round_trip_grid() -> None:
    """Ensure IV solver recovers known sigma within 1e-4 tolerance."""
    s = 10.50
    k = 10.00
    t = 0.50
    r = 0.03

    sigmas = [0.10, 0.20, 0.35, 0.50, 0.80, 1.20, 1.80]
    for target_sigma in sigmas:
        price = bs_price(s=s, k=k, t=t, r=r, sigma=target_sigma, option_type="call")
        res = solve_iv(price=price, s=s, k=k, t=t, r=r, option_type="call")
        assert res.iv is not None, f"Failed to solve for sigma={target_sigma}: {res.reason_code}"
        assert abs(res.iv - target_sigma) < 1e-4, f"Target {target_sigma} != recovered {res.iv}"
        assert res.reason_code is None


def test_iv_below_intrinsic() -> None:
    """Option priced below discounted intrinsic value must return below_intrinsic reason."""
    s = 10.0
    k = 8.0
    t = 1.0
    r = 0.05
    # Discounted intrinsic is 10.0 - 8.0 * exp(-0.05) ~ 2.389
    # If price is 1.50, it is below intrinsic arbitrage bound
    res = solve_iv(price=1.50, s=s, k=k, t=t, r=r, option_type="call")
    assert res.iv is None
    assert res.reason_code == "below_intrinsic"


def test_iv_above_upper_bound() -> None:
    """Call price greater than underlying price violates upper bound."""
    s = 10.0
    k = 10.0
    t = 0.5
    r = 0.03
    # Call price of 12.0 when S=10.0
    res = solve_iv(price=12.0, s=s, k=k, t=t, r=r, option_type="call")
    assert res.iv is None
    assert res.reason_code == "above_upper_bound"


def test_iv_non_positive_and_no_quote() -> None:
    """Non-positive or missing prices return appropriate codes."""
    res_zero = solve_iv(price=0.0, s=10.0, k=10.0, t=0.5, r=0.03, option_type="call")
    assert res_zero.iv is None
    assert res_zero.reason_code == "non_positive_price"

    res_none = solve_iv(price=None, s=10.0, k=10.0, t=0.5, r=0.03, option_type="call")
    assert res_none.iv is None
    assert res_none.reason_code == "no_quote"


def test_iv_expired() -> None:
    """Time to expiry <= 0 returns expired code."""
    res_exp = solve_iv(price=0.08, s=10.0, k=10.0, t=0.0, r=0.03, option_type="call")
    assert res_exp.iv is None
    assert res_exp.reason_code == "expired"


def test_iv_by_basis() -> None:
    """Multi-basis evaluation computes IV for bid, mid, ask, size_weighted_mid, last."""
    s = 10.0
    k = 11.0  # OTM call has lower bound = 0.0
    t = 0.5
    r = 0.03

    bid = 0.080
    ask = 0.100
    mid = 0.090
    sw_mid = 0.088
    last = 0.090

    results = iv_by_basis(
        bid=bid,
        mid=mid,
        ask=ask,
        size_weighted_mid=sw_mid,
        last=last,
        s=s,
        k=k,
        t=t,
        r=r,
        option_type="call",
    )

    for basis in ("bid", "mid", "ask", "size_weighted_mid", "last"):
        assert basis in results
        assert results[basis].iv is not None
        assert 0.0 < results[basis].iv < 2.0

    # Bid IV < Mid IV < Ask IV
    assert results["bid"].iv < results["mid"].iv < results["ask"].iv

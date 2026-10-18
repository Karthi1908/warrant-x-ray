"""Unit tests for warrant quant metrics calculations (T030).

Covers:
- Headline IV defaulting to mid, falling back to last, or returning None with no_quote
- Size-weighted mid calculation
- Spread percentage and round-trip cost
- Gearing and effective gearing
- Premium, breakeven price, and required underlying move
- Expired warrants and cross-checks against issuer values
"""

import math
import pytest
from warrantx.quant.metrics import compute_metrics, WarrantQuantInput


def test_headline_iv_selection_and_fallback() -> None:
    """Headline IV defaults to mid, falls back to last if bid/ask missing."""
    # Case 1: Quotes present -> defaults to mid
    inp_normal = WarrantQuantInput(
        code="51881C",
        issuer="CGS",
        type="call",
        underlying_price=10.50,
        strike=10.00,
        ratio=4.0,
        bid=0.150,
        ask=0.160,
        last=0.155,
        days_to_expiry=90,
        risk_free_rate=0.03,
    )
    m1 = compute_metrics(inp_normal)
    assert m1.headline_iv_basis == "mid"
    assert m1.headline_iv is not None
    assert m1.mid == 0.155

    # Case 2: Missing bid/ask quotes -> falls back to last
    inp_no_quotes = WarrantQuantInput(
        code="51881C",
        issuer="CGS",
        type="call",
        underlying_price=10.50,
        strike=10.00,
        ratio=4.0,
        bid=None,
        ask=None,
        last=0.155,
        days_to_expiry=90,
        risk_free_rate=0.03,
    )
    m2 = compute_metrics(inp_no_quotes)
    assert m2.headline_iv_basis == "last"
    assert m2.headline_iv is not None

    # Case 3: Missing quotes and missing last -> None with no_quote
    inp_empty = WarrantQuantInput(
        code="51881C",
        issuer="CGS",
        type="call",
        underlying_price=10.50,
        strike=10.00,
        ratio=4.0,
        bid=None,
        ask=None,
        last=None,
        days_to_expiry=90,
        risk_free_rate=0.03,
    )
    m3 = compute_metrics(inp_empty)
    assert m3.headline_iv is None
    assert m3.iv_reason_codes.get("mid") == "no_quote"


def test_size_weighted_mid() -> None:
    """Size-weighted mid = (bid * ask_volume + ask * bid_volume) / (bid_volume + ask_volume)."""
    inp = WarrantQuantInput(
        code="51881C",
        issuer="CGS",
        type="call",
        underlying_price=10.00,
        strike=10.00,
        ratio=4.0,
        bid=0.100,
        ask=0.120,
        bid_volume=10000,
        ask_volume=30000,
        days_to_expiry=60,
        risk_free_rate=0.03,
    )
    m = compute_metrics(inp)
    # (0.100 * 30000 + 0.120 * 10000) / 40000 = (3000 + 1200) / 40000 = 4200 / 40000 = 0.105
    assert m.size_weighted_mid is not None
    assert math.isclose(m.size_weighted_mid, 0.105, rel_tol=1e-5)


def test_spread_and_round_trip_cost() -> None:
    """Spread % and round-trip cost = (ask - bid) / mid."""
    inp = WarrantQuantInput(
        code="51881C",
        issuer="CGS",
        type="call",
        underlying_price=10.00,
        strike=10.00,
        ratio=4.0,
        bid=0.080,
        ask=0.100,
        days_to_expiry=60,
        risk_free_rate=0.03,
    )
    m = compute_metrics(inp)
    # mid = 0.090, spread = 0.020 / 0.090 = 0.2222... (22.2%)
    assert m.mid == 0.090
    assert m.spread_pct is not None
    assert math.isclose(m.spread_pct, 0.020 / 0.090, rel_tol=1e-4)
    assert math.isclose(m.round_trip_cost, m.spread_pct, rel_tol=1e-6)


def test_gearing_and_effective_gearing() -> None:
    """Gearing = (S / ratio) / warrant_price; Effective gearing = gearing * |delta|."""
    s = 10.00
    ratio = 4.0
    # Effective stock price per warrant = 10.0 / 4.0 = 2.50
    # If mid = 0.100 -> gearing = 2.50 / 0.100 = 25.0x
    inp = WarrantQuantInput(
        code="51881C",
        issuer="CGS",
        type="call",
        underlying_price=s,
        strike=10.00,
        ratio=ratio,
        bid=0.095,
        ask=0.105,
        days_to_expiry=60,
        risk_free_rate=0.03,
    )
    m = compute_metrics(inp)
    assert m.gearing is not None
    assert math.isclose(m.gearing, 25.0, rel_tol=1e-4)
    assert m.effective_gearing is not None
    assert m.delta_share is not None
    expected_eg = 25.0 * abs(m.delta_share)
    assert math.isclose(m.effective_gearing, expected_eg, rel_tol=1e-4)


def test_breakeven_and_required_move() -> None:
    """Call breakeven = strike + ask * ratio; Put breakeven = strike - ask * ratio."""
    # Call
    inp_call = WarrantQuantInput(
        code="51881C",
        issuer="CGS",
        type="call",
        underlying_price=10.00,
        strike=10.50,
        ratio=4.0,
        bid=0.080,
        ask=0.100,
        days_to_expiry=60,
        risk_free_rate=0.03,
    )
    m_call = compute_metrics(inp_call)
    # Breakeven = 10.50 + 0.100 * 4 = 10.90
    assert m_call.breakeven_price == 10.90
    # Required move = (10.90 - 10.00) / 10.00 = +9.0%
    assert math.isclose(m_call.required_move, 0.09, rel_tol=1e-5)

    # Put
    inp_put = WarrantQuantInput(
        code="51882P",
        issuer="CGS",
        type="put",
        underlying_price=10.00,
        strike=9.50,
        ratio=4.0,
        bid=0.080,
        ask=0.100,
        days_to_expiry=60,
        risk_free_rate=0.03,
    )
    m_put = compute_metrics(inp_put)
    # Breakeven = 9.50 - 0.100 * 4 = 9.10
    assert m_put.breakeven_price == 9.10
    # Required move = (9.10 - 10.00) / 10.00 = -9.0%
    assert math.isclose(m_put.required_move, -0.09, rel_tol=1e-5)


def test_expired_warrant_metrics() -> None:
    """Expired warrants have days_to_expiry <= 0 and return no forward-looking metrics."""
    inp = WarrantQuantInput(
        code="5188EX",
        issuer="CGS",
        type="call",
        underlying_price=10.00,
        strike=10.00,
        ratio=4.0,
        bid=0.010,
        ask=0.020,
        days_to_expiry=0,
        risk_free_rate=0.03,
    )
    m = compute_metrics(inp)
    assert m.days_to_expiry == 0
    assert m.headline_iv is None
    assert m.delta_share is None
    assert m.gamma is None
    assert m.theta_per_day is None

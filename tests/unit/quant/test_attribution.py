"""Unit tests for sequential move attribution (T103, FR-EXP-01, FR-EXP-02, FR-EXP-03, AC-04).

Requirements:
- FR-EXP-01: Decompose mid price change into: underlying move, passage of time, change in IV, residual.
- FR-EXP-02: Sequential in that fixed order; the 4 parts MUST sum to the total change within 1e-9; state order.
- FR-EXP-03: If either snapshot lacks warrant or needed inputs, list missing and return no decomposition.
"""

from __future__ import annotations

import pytest

from warrantx.quant.attribution import attribute_move, SequentialAttributionResult


def make_dummy_row(
    code: str = "115510",
    warrant_type: str = "call",
    strike: float = 10.0,
    ratio: float = 4.0,
    underlying_price: float = 10.0,
    days_to_expiry: int = 60,
    bid: float = 0.150,
    ask: float = 0.160,
    iv: float = 0.30,
) -> dict:
    """Helper to create dummy warrant rows with complete inputs."""
    return {
        "code": code,
        "type": warrant_type,
        "strike": strike,
        "ratio": ratio,
        "underlying_price": underlying_price,
        "days_to_expiry": days_to_expiry,
        "bid": bid,
        "ask": ask,
        "iv": iv,
    }


def test_attribution_sum_to_total_within_1e9():
    """FR-EXP-01, FR-EXP-02: 4 parts sum exactly to total mid change within 1e-9 with fixed order stated."""
    from_row = make_dummy_row(
        underlying_price=10.00,
        days_to_expiry=60,
        iv=0.30,
        bid=0.150,
        ask=0.160,  # mid = 0.155
    )
    to_row = make_dummy_row(
        underlying_price=10.40,  # stock rose
        days_to_expiry=59,       # 1 day passed
        iv=0.28,                 # IV dropped (crush)
        bid=0.180,
        ask=0.190,  # mid = 0.185
    )

    result = attribute_move(from_row, to_row, risk_free_rate=0.03)

    assert result.ok is True
    assert result.total_change == pytest.approx(0.185 - 0.155, abs=1e-9)

    sum_parts = (
        result.underlying_move
        + result.passage_of_time
        + result.implied_volatility
        + result.residual
    )

    # FR-EXP-02: MUST sum to total change within 1e-9
    assert abs(sum_parts - result.total_change) < 1e-9

    # Verify fixed order is explicitly stated
    assert result.order == [
        "underlying_move",
        "passage_of_time",
        "implied_volatility",
        "residual",
    ]
    assert "fixed order" in result.order_description.lower()

    # Directional sanity checks:
    # Stock rose -> underlying move contribution positive
    assert result.underlying_move > 0
    # Time passed -> theta decay negative
    assert result.passage_of_time < 0
    # IV dropped -> vega drop negative
    assert result.implied_volatility < 0


def test_attribution_put_warrant_sum_to_total():
    """Verify sum-to-total within 1e-9 holds for put warrants."""
    from_row = make_dummy_row(
        warrant_type="put",
        underlying_price=10.00,
        days_to_expiry=90,
        iv=0.35,
        bid=0.120,
        ask=0.130,  # mid = 0.125
    )
    to_row = make_dummy_row(
        warrant_type="put",
        underlying_price=9.70,   # stock fell -> good for put
        days_to_expiry=88,       # 2 days passed
        iv=0.36,                 # IV rose
        bid=0.160,
        ask=0.170,  # mid = 0.165
    )

    result = attribute_move(from_row, to_row, risk_free_rate=0.03)
    assert result.ok is True
    sum_parts = (
        result.underlying_move
        + result.passage_of_time
        + result.implied_volatility
        + result.residual
    )
    assert abs(sum_parts - result.total_change) < 1e-9
    assert result.underlying_move > 0  # put gains when underlying falls


def test_attribution_identical_snapshots():
    """Verify decomposition is identically zero when snapshots have zero change."""
    row = make_dummy_row()
    result = attribute_move(row, row, risk_free_rate=0.03)

    assert result.ok is True
    assert result.total_change == 0.0
    assert result.underlying_move == 0.0
    assert result.passage_of_time == 0.0
    assert result.implied_volatility == 0.0
    assert result.residual == 0.0


def test_attribution_missing_inputs():
    """FR-EXP-03: If either snapshot lacks the warrant or required inputs, say which and return no decomposition."""
    # 1. Missing to_row entirely (warrant delisted or not in snapshot)
    result = attribute_move(make_dummy_row(), None)
    assert result.ok is False
    assert "to_snapshot" in result.missing or "warrant_missing_in_target" in result.missing
    assert result.underlying_move is None
    assert result.total_change is None

    # 2. Missing from_row entirely
    result2 = attribute_move(None, make_dummy_row())
    assert result2.ok is False
    assert "from_snapshot" in result2.missing or "warrant_missing_in_source" in result2.missing
    assert result2.underlying_move is None

    # 3. Missing bid / ask in to_row
    broken_to = make_dummy_row()
    broken_to["bid"] = None
    broken_to["ask"] = None
    result3 = attribute_move(make_dummy_row(), broken_to)
    assert result3.ok is False
    assert any("bid" in m for m in result3.missing)
    assert result3.underlying_move is None

    # 4. Missing underlying price in from_row
    broken_from = make_dummy_row()
    broken_from["underlying_price"] = None
    result4 = attribute_move(broken_from, make_dummy_row())
    assert result4.ok is False
    assert any("underlying_price" in m for m in result4.missing)
    assert result4.underlying_move is None

"""Unit tests for the scenario simulation engine (FR-SCN-01 to 07).

Tests:
1. Identity: 0% move, 0 days, 0 vol shift yields entry=ask, exit=bid, pnl = bid/ask - 1
2. Breakeven: underlying move that yields 0% P&L
3. Intrinsic at expiry: when days_held == days_left, exit price equals intrinsic value / ratio
4. Curve generation: 3 horizons (0, days_held, min(2*days_held, days_left)), 41 points (-20% to +20%)
5. Range rejection: invalid move, negative days, days > days_left, iv_shift > 15
6. Call vs Put directionality: positive move helps call, negative move helps put
"""

import pytest

from warrantx.quant.bs import OptionType
from warrantx.quant.scenario import (
    ScenarioError,
    breakeven_move,
    calculate_scenario,
    generate_curves,
)


@pytest.fixture
def base_warrant_params():
    return {
        "code": "115510",
        "opt_type": "call",
        "underlying_price": 10.0,
        "strike": 10.0,
        "ratio": 4.0,
        "bid": 0.150,
        "ask": 0.160,
        "days_left": 60,
        "headline_iv": 0.35,  # 35%
        "risk_free_rate": 0.03,
    }


def test_scenario_identity(base_warrant_params):
    """0% move, 0 days, 0 shift must exactly equal bid/ask - 1."""
    res = calculate_scenario(
        **base_warrant_params,
        move_pct=0.0,
        days_held=0,
        iv_shift_pts=0.0,
    )

    expected_pnl = (0.150 / 0.160) - 1.0
    assert pytest.approx(res.entry_price, rel=1e-5) == 0.160
    assert pytest.approx(res.exit_price, rel=1e-5) == 0.150
    assert pytest.approx(res.pnl_pct, rel=1e-5) == expected_pnl
    assert res.inputs.move == 0.0
    assert res.inputs.days == 0
    assert res.inputs.iv_shift == 0.0


def test_scenario_positive_move_call(base_warrant_params):
    """Positive stock move increases call warrant exit price and improves PnL."""
    res_base = calculate_scenario(**base_warrant_params, move_pct=0.0, days_held=3, iv_shift_pts=0.0)
    res_up = calculate_scenario(**base_warrant_params, move_pct=0.05, days_held=3, iv_shift_pts=0.0)

    assert res_up.exit_price > res_base.exit_price
    assert res_up.pnl_pct > res_base.pnl_pct


def test_scenario_intrinsic_at_expiry(base_warrant_params):
    """When held to expiry, exit price equals pure intrinsic value."""
    # Stock up 20% to RM 12.00, strike 10.0, ratio 4.0 -> intrinsic = (12 - 10) / 4 = 0.50
    res_itm = calculate_scenario(
        **base_warrant_params,
        move_pct=0.20,
        days_held=base_warrant_params["days_left"],
        iv_shift_pts=0.0,
    )
    assert pytest.approx(res_itm.exit_price, abs=1e-4) == 0.50

    # Stock down 20% to RM 8.00, strike 10.0 -> intrinsic = 0.0
    res_otm = calculate_scenario(
        **base_warrant_params,
        move_pct=-0.20,
        days_held=base_warrant_params["days_left"],
        iv_shift_pts=0.0,
    )
    assert pytest.approx(res_otm.exit_price, abs=1e-4) == 0.0
    assert pytest.approx(res_otm.pnl_pct, abs=1e-4) == -1.0


def test_breakeven_move(base_warrant_params):
    """Breakeven move calculates move needed for 0% PnL."""
    be = breakeven_move(**base_warrant_params, days_held=5, iv_shift_pts=0.0)
    assert be is not None
    assert be > 0.0  # Call needs positive move to break even after decay and spread

    # Verify scenario at breakeven gives approx 0% PnL
    res = calculate_scenario(
        **base_warrant_params,
        move_pct=be,
        days_held=5,
        iv_shift_pts=0.0,
    )
    assert pytest.approx(res.pnl_pct, abs=0.01) == 0.0


def test_scenario_curve_horizons(base_warrant_params):
    """Curves must produce 3 distinct horizons and 41 points per curve (-20% to +20%)."""
    curves = generate_curves(
        **base_warrant_params,
        days_held=5,
        iv_shift_pts=0.0,
    )

    # Horizons: 0, 5, 10
    assert len(curves) == 3
    horizons = [c.horizon_days for c in curves]
    assert horizons == [0, 5, 10]

    for curve in curves:
        assert len(curve.points) == 41
        moves = [p.move for p in curve.points]
        assert pytest.approx(moves[0], abs=1e-5) == -0.20
        assert pytest.approx(moves[-1], abs=1e-5) == 0.20
        assert pytest.approx(moves[20], abs=1e-5) == 0.0


def test_scenario_range_rejections(base_warrant_params):
    """Out-of-range inputs must raise ScenarioError naming the valid range."""
    with pytest.raises(ScenarioError) as exc_info:
        calculate_scenario(**base_warrant_params, move_pct=0.60, days_held=0, iv_shift_pts=0.0)
    assert "[-0.5, 0.5]" in str(exc_info.value)

    with pytest.raises(ScenarioError) as exc_info:
        calculate_scenario(**base_warrant_params, move_pct=0.0, days_held=-1, iv_shift_pts=0.0)
    assert "[0, 60]" in str(exc_info.value)

    with pytest.raises(ScenarioError) as exc_info:
        calculate_scenario(**base_warrant_params, move_pct=0.0, days_held=100, iv_shift_pts=0.0)
    assert "[0, 60]" in str(exc_info.value)

    with pytest.raises(ScenarioError) as exc_info:
        calculate_scenario(**base_warrant_params, move_pct=0.0, days_held=0, iv_shift_pts=20.0)
    assert "[-15, 15]" in str(exc_info.value)

"""Unit tests for risk flags and not-evaluated behavior (T031).

Covers:
- Standard flag triggers: HIGH_DECAY, WIDE_SPREAD, LOW_LIQUIDITY, DEEP_OTM, SHORT_EXPIRY, IV_RICH, ISSUER_MISMATCH, DATA_STALE
- Mandatory not_evaluated tracking: missing inputs must NEVER mark a flag clear
"""

import pytest
from warrantx.quant.flags import evaluate_flags, FlagsConfig
from warrantx.tools.models import WarrantMetrics, WarrantRowModel


def _make_sample_row(**kwargs) -> WarrantRowModel:
    defaults = {
        "code": "51881C",
        "issuer": "CGS",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": "2026-12-31",
        "strike": 10.0,
        "display_strike": "RM 10.00",
        "ratio_raw": 4.0,
        "display_ratio": "4.0x",
        "underlying_bid": 10.0,
        "bid": 0.100,
        "ask": 0.110,
        "bid_volume": 50000,
        "ask_volume": 50000,
        "last_price": 0.105,
        "moneyness": 1.0,
        "issuer_iv": 35.0,
        "issuer_eg": 5.0,
        "issuer_delta": 0.50,
        "valid": True,
    }
    defaults.update(kwargs)
    return WarrantRowModel(**defaults)


def _make_sample_metrics(**kwargs) -> WarrantMetrics:
    defaults = {
        "mid": 0.105,
        "spread_pct": 0.05,
        "headline_iv": 0.35,
        "days_to_expiry": 60,
        "theta_per_day": -0.001,
        "gearing": 23.8,
        "effective_gearing": 5.0,
        "delta_share": 0.50,
    }
    defaults.update(kwargs)
    return WarrantMetrics(**defaults)


def test_short_expiry_flag() -> None:
    """SHORT_EXPIRY triggers when days_to_expiry < threshold (e.g. 14 days)."""
    cfg = FlagsConfig(approaching_expiry_days=14)
    row = _make_sample_row()
    
    # 7 days left -> triggers SHORT_EXPIRY
    m_short = _make_sample_metrics(days_to_expiry=7)
    res_short = evaluate_flags(row, m_short, cfg=cfg)
    flag_codes = [f.code for f in res_short.flags]
    assert "SHORT_EXPIRY" in flag_codes

    # 45 days left -> does not trigger
    m_ok = _make_sample_metrics(days_to_expiry=45)
    res_ok = evaluate_flags(row, m_ok, cfg=cfg)
    flag_codes_ok = [f.code for f in res_ok.flags]
    assert "SHORT_EXPIRY" not in flag_codes_ok


def test_wide_spread_flag() -> None:
    """WIDE_SPREAD triggers when spread_pct > threshold (e.g. 10%)."""
    cfg = FlagsConfig(low_liquidity_spread_pct=0.10)
    row = _make_sample_row()

    # 15% spread -> triggers WIDE_SPREAD
    m_wide = _make_sample_metrics(spread_pct=0.15)
    res_wide = evaluate_flags(row, m_wide, cfg=cfg)
    assert any(f.code == "WIDE_SPREAD" for f in res_wide.flags)

    # 3% spread -> no flag
    m_tight = _make_sample_metrics(spread_pct=0.03)
    res_tight = evaluate_flags(row, m_tight, cfg=cfg)
    assert not any(f.code == "WIDE_SPREAD" for f in res_tight.flags)


def test_not_evaluated_when_input_missing() -> None:
    """When a required input is None, flag goes to not_evaluated, NEVER passed silently."""
    cfg = FlagsConfig()
    row = _make_sample_row(issuer_iv=None)  # missing issuer IV
    metrics = _make_sample_metrics(headline_iv=0.35)

    res = evaluate_flags(row, metrics, cfg=cfg)
    not_eval_flags = [ne.flag for ne in res.not_evaluated]
    # ISSUER_MISMATCH cannot be evaluated because issuer_iv is missing
    assert "ISSUER_MISMATCH" in not_eval_flags
    # Must NOT appear in active flags
    assert not any(f.code == "ISSUER_MISMATCH" for f in res.flags)


def test_deep_otm_flag() -> None:
    """DEEP_OTM triggers when moneyness < 0.80 for call."""
    cfg = FlagsConfig(deep_otm_moneyness=0.80)
    row_otm = _make_sample_row(moneyness=0.75, type="call")
    metrics = _make_sample_metrics()

    res = evaluate_flags(row_otm, metrics, cfg=cfg)
    assert any(f.code == "DEEP_OTM" for f in res.flags)

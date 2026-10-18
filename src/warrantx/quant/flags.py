"""Warrant risk flags engine and cost-of-holding presets.

Evaluates thresholds for:
- SHORT_EXPIRY
- WIDE_SPREAD
- LOW_LIQUIDITY
- DEEP_OTM
- HIGH_DECAY
- IV_RICH
- ISSUER_MISMATCH
- DATA_STALE

Crucial rule: A flag with missing input is marked in `not_evaluated`, NEVER passed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from warrantx.tools.evidence import (
    format_currency,
    format_percent,
    format_ratio,
)
from warrantx.tools.models import (
    FlagItem,
    HoldingCostPresets,
    NotEvaluatedFlag,
    WarrantMetrics,
    WarrantRowModel,
)


@dataclass
class FlagsConfig:
    """Threshold configuration for risk flags."""

    approaching_expiry_days: int = 14
    low_liquidity_spread_pct: float = 0.10
    deep_otm_moneyness: float = 0.80
    high_decay_theta_pct: float = 0.02
    high_effective_gearing: float = 10.0
    issuer_mismatch_iv_points: float = 3.0
    issuer_mismatch_eg_pct: float = 0.15
    issuer_mismatch_delta: float = 0.10
    min_quote_volume: int = 5000


@dataclass
class FlagsResult:
    """Outcome of flag evaluation."""

    flags: list[FlagItem]
    not_evaluated: list[NotEvaluatedFlag]


def evaluate_flags(
    row: WarrantRowModel,
    metrics: WarrantMetrics,
    realized_vol_30d: float | None = None,
    cfg: FlagsConfig | None = None,
) -> FlagsResult:
    """Evaluate all standardized risk flags for a warrant."""
    if cfg is None:
        cfg = FlagsConfig()

    flags: list[FlagItem] = []
    not_evaluated: list[NotEvaluatedFlag] = []

    # 1. SHORT_EXPIRY
    if metrics.days_to_expiry is not None:
        if metrics.days_to_expiry < cfg.approaching_expiry_days:
            flags.append(
                FlagItem(
                    code="SHORT_EXPIRY",
                    severity="high" if metrics.days_to_expiry <= 7 else "warn",
                    threshold=f"< {cfg.approaching_expiry_days} days",
                    value=f"{metrics.days_to_expiry} days",
                    text=f"Approaching expiry in {metrics.days_to_expiry} days; time decay accelerates rapidly.",
                )
            )
    else:
        not_evaluated.append(NotEvaluatedFlag(flag="SHORT_EXPIRY", reason="days_to_expiry missing"))

    # 2. WIDE_SPREAD
    if metrics.spread_pct is not None:
        if metrics.spread_pct > cfg.low_liquidity_spread_pct:
            pct_str = f"{metrics.spread_pct * 100.0:.1f}%"
            thresh_str = f"> {cfg.low_liquidity_spread_pct * 100.0:.1f}%"
            flags.append(
                FlagItem(
                    code="WIDE_SPREAD",
                    severity="high" if metrics.spread_pct > 0.20 else "warn",
                    threshold=thresh_str,
                    value=pct_str,
                    text=f"Wide bid-ask spread of {pct_str} creates high immediate round-trip cost.",
                )
            )
    else:
        not_evaluated.append(NotEvaluatedFlag(flag="WIDE_SPREAD", reason="bid/ask quotes missing"))

    # 3. LOW_LIQUIDITY
    if row.bid_volume is None or row.ask_volume is None or row.bid is None:
        if row.bid is None or row.bid == 0.0:
            flags.append(
                FlagItem(
                    code="LOW_LIQUIDITY",
                    severity="high",
                    threshold="No bid buyer quote",
                    value="0 bids",
                    text="Zero bid quotes in orderbook; market maker liquidity absent.",
                )
            )
        else:
            not_evaluated.append(
                NotEvaluatedFlag(flag="LOW_LIQUIDITY", reason="quote volumes missing")
            )
    else:
        min_vol = min(row.bid_volume, row.ask_volume)
        if min_vol < cfg.min_quote_volume:
            flags.append(
                FlagItem(
                    code="LOW_LIQUIDITY",
                    severity="warn",
                    threshold=f"< {cfg.min_quote_volume:,} units",
                    value=f"{min_vol:,} units",
                    text=f"Order book depth is thin ({min_vol:,} units), risking slippage.",
                )
            )

    # 4. DEEP_OTM
    if row.moneyness is not None:
        is_deep = False
        if row.type.lower() == "call" and row.moneyness < cfg.deep_otm_moneyness:
            is_deep = True
        elif row.type.lower() == "put" and row.moneyness > (2.0 - cfg.deep_otm_moneyness):
            is_deep = True

        if is_deep:
            flags.append(
                FlagItem(
                    code="DEEP_OTM",
                    severity="high",
                    threshold=f"< {cfg.deep_otm_moneyness:.2f}",
                    value=f"{row.moneyness:.2f}",
                    text="Deep out-of-the-money warrant with very low delta; high risk of expiring worthless.",
                )
            )
    else:
        not_evaluated.append(NotEvaluatedFlag(flag="DEEP_OTM", reason="moneyness missing"))

    # 5. HIGH_DECAY
    if metrics.theta_per_day is not None and metrics.mid is not None and metrics.mid > 0:
        daily_decay_pct = abs(metrics.theta_per_day) / metrics.mid
        if daily_decay_pct > cfg.high_decay_theta_pct:
            pct_str = f"{daily_decay_pct * 100.0:.1f}%/day"
            flags.append(
                FlagItem(
                    code="HIGH_DECAY",
                    severity="high" if daily_decay_pct > 0.05 else "warn",
                    threshold=f"> {cfg.high_decay_theta_pct * 100.0:.1f}%/day",
                    value=pct_str,
                    text=f"Steep time decay eroding {pct_str} of warrant value every single day.",
                )
            )
    else:
        not_evaluated.append(
            NotEvaluatedFlag(flag="HIGH_DECAY", reason="theta or mid price missing")
        )

    # 6. IV_RICH
    if metrics.headline_iv is not None and realized_vol_30d is not None:
        iv_pts = metrics.headline_iv * 100.0
        rv_pts = realized_vol_30d * 100.0
        if (iv_pts - rv_pts) > 15.0:  # 15 points rich
            flags.append(
                FlagItem(
                    code="IV_RICH",
                    severity="warn",
                    threshold=f"> RV + 15 pts ({rv_pts:.1f} pts)",
                    value=f"{iv_pts:.1f} pts",
                    text=f"Implied volatility ({iv_pts:.1f} pts) is significantly elevated above 30d realized volatility.",
                )
            )
    else:
        not_evaluated.append(
            NotEvaluatedFlag(flag="IV_RICH", reason="realized volatility 30d not available")
        )

    # 7. ISSUER_MISMATCH
    if (
        row.issuer_iv is None
        or metrics.headline_iv is None
    ):
        not_evaluated.append(
            NotEvaluatedFlag(flag="ISSUER_MISMATCH", reason="issuer published metrics or headline IV missing")
        )
    else:
        mismatch_notes: list[str] = []
        if (
            metrics.headline_iv is not None
            and row.issuer_iv is not None
            and abs((metrics.headline_iv * 100.0) - row.issuer_iv) > cfg.issuer_mismatch_iv_points
        ):
            mismatch_notes.append(
                f"IV diff: {abs((metrics.headline_iv * 100.0) - row.issuer_iv):.1f} pts"
            )

        if (
            metrics.effective_gearing is not None
            and row.issuer_eg is not None
            and row.issuer_eg != 0
            and abs(metrics.effective_gearing - row.issuer_eg) / abs(row.issuer_eg)
            > cfg.issuer_mismatch_eg_pct
        ):
            mismatch_notes.append(
                f"EG diff: {abs(metrics.effective_gearing - row.issuer_eg) / abs(row.issuer_eg) * 100.0:.1f}%"
            )

        if mismatch_notes:
            flags.append(
                FlagItem(
                    code="ISSUER_MISMATCH",
                    severity="warn",
                    threshold="Significant deviation from issuer matrix",
                    value=", ".join(mismatch_notes),
                    text="Discrepancy detected between issuer published metrics and Black-Scholes recalculation.",
                )
            )

    return FlagsResult(flags=flags, not_evaluated=not_evaluated)


def compute_holding_cost_presets(
    metrics: WarrantMetrics, holding_days: int = 5
) -> HoldingCostPresets:
    """Calculate the cost-of-holding preset estimates for a given duration."""
    # 1. Spread cost
    spread_cost = metrics.spread_pct

    # 2. Flat decay over holding duration
    flat_decay: float | None = None
    if metrics.theta_per_day is not None and metrics.mid is not None and metrics.mid > 0:
        flat_decay = abs(metrics.theta_per_day * holding_days) / metrics.mid

    # 3. IV Crush estimate: -5 points IV drop
    iv_crush: float | None = None
    if metrics.vega_per_point is not None and metrics.mid is not None and metrics.mid > 0:
        iv_crush = abs(metrics.vega_per_point * 5.0) / metrics.mid

    # 4. Gearing check
    gearing_check = metrics.effective_gearing

    # 5. Breakeven move
    breakeven_move = metrics.required_move

    return HoldingCostPresets(
        spread_cost=spread_cost,
        display_spread_cost=format_percent(spread_cost),
        flat_decay=flat_decay,
        display_flat_decay=format_percent(flat_decay),
        iv_crush=iv_crush,
        display_iv_crush=format_percent(iv_crush),
        gearing_check=gearing_check,
        display_gearing_check=format_ratio(gearing_check),
        breakeven_move=breakeven_move,
        display_breakeven_move=format_percent(breakeven_move, signed=True),
    )

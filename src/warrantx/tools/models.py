"""Pydantic models for Warrant X-Ray tools, API, and evidence payloads.

Every numeric metric has a raw numeric value and a server-formatted display string.
Unknown values are None.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

# Re-export Evidence and formatting helpers for unified access
from warrantx.tools.evidence import (
    Evidence,
    collect_display_strings,
    format_currency,
    format_days,
    format_greek,
    format_int,
    format_percent,
    format_points,
    format_ratio,
)


class WarrantRowModel(BaseModel):
    """Single warrant row inside a snapshot."""

    code: str
    issuer: str
    type: str  # "call" | "put"
    underlying_ticker: str
    expiry_date: str  # YYYY-MM-DD
    strike: float
    display_strike: str
    ratio_raw: float
    display_ratio: str
    underlying_bid: float | None = None
    display_underlying_bid: str | None = None
    bid: float | None = None
    display_bid: str | None = None
    ask: float | None = None
    display_ask: str | None = None
    bid_volume: int | None = None
    ask_volume: int | None = None
    traded_volume: int | None = None
    last_price: float | None = None
    display_last_price: str | None = None
    last_time: str | None = None
    issuer_iv: float | None = None
    display_issuer_iv: str | None = None
    issuer_eg: float | None = None
    display_issuer_eg: str | None = None
    issuer_delta: float | None = None
    display_issuer_delta: str | None = None
    issuer_premium: float | None = None
    display_issuer_premium: str | None = None
    issuer_theta_raw: float | None = None
    display_issuer_theta_raw: str | None = None
    sensitivity_ticks: float | None = None
    moneyness: float | None = None
    indicators: dict[str, bool] | None = None
    valid: bool = True


class WarrantSnapshot(BaseModel):
    """Market snapshot containing warrant rows and data quality metadata."""

    id: int
    fetched_at: str
    source_last_update: str | None = None
    row_count: int = 0
    ok: bool = True
    note: str = ""
    suspect: bool = False
    quality: dict[str, Any] | None = None
    warrants: list[WarrantRowModel] = Field(default_factory=list)


class WarrantMetrics(BaseModel):
    """Calculated quant metrics for a warrant."""

    shares_per_warrant: float | None = None
    display_shares_per_warrant: str | None = None
    days_to_expiry: int | None = None
    display_days_to_expiry: str | None = None
    mid: float | None = None
    display_mid: str | None = None
    size_weighted_mid: float | None = None
    display_size_weighted_mid: str | None = None
    spread_pct: float | None = None
    display_spread_pct: str | None = None
    round_trip_cost: float | None = None
    display_round_trip_cost: str | None = None
    iv_by_basis: dict[str, float | None] = Field(default_factory=dict)
    iv_reason_codes: dict[str, str | None] = Field(default_factory=dict)
    headline_iv: float | None = None
    display_headline_iv: str | None = None
    headline_iv_basis: str = "mid"
    iv_basis_spread: float | None = None
    display_iv_basis_spread: str | None = None
    delta_share: float | None = None
    display_delta_share: str | None = None
    gamma: float | None = None
    display_gamma: str | None = None
    vega_per_point: float | None = None
    display_vega_per_point: str | None = None
    theta_per_day: float | None = None
    display_theta_per_day: str | None = None
    gearing: float | None = None
    display_gearing: str | None = None
    effective_gearing: float | None = None
    display_effective_gearing: str | None = None
    premium: float | None = None
    display_premium: str | None = None
    breakeven_price: float | None = None
    display_breakeven_price: str | None = None
    required_move: float | None = None
    display_required_move: str | None = None
    cross_check: dict[str, float | None] | None = None


class FlagItem(BaseModel):
    """Individual risk flag triggered on a warrant."""

    code: str
    severity: str  # "warn" | "high"
    threshold: str | float
    value: str | float | None = None
    text: str


class NotEvaluatedFlag(BaseModel):
    """Flag that could not be evaluated due to missing or invalid inputs."""

    flag: str
    reason: str


class HoldingCostPresets(BaseModel):
    """Holding cost preset breakdowns."""

    spread_cost: float | None = None
    display_spread_cost: str | None = None
    flat_decay: float | None = None
    display_flat_decay: str | None = None
    iv_crush: float | None = None
    display_iv_crush: str | None = None
    gearing_check: float | None = None
    display_gearing_check: str | None = None
    breakeven_move: float | None = None
    display_breakeven_move: str | None = None


class WarrantCard(BaseModel):
    """Full warrant card payload with metrics, cost presets, flags, and cross-checks."""

    code: str
    issuer: str
    type: str
    underlying_ticker: str
    expiry_date: str
    strike: float
    display_strike: str
    ratio_raw: float
    display_ratio: str
    underlying_price: float | None = None
    display_underlying_price: str | None = None
    bid: float | None = None
    display_bid: str | None = None
    ask: float | None = None
    display_ask: str | None = None
    metrics: WarrantMetrics
    holding_days: int = 5
    presets: HoldingCostPresets = Field(default_factory=HoldingCostPresets)
    flags: list[FlagItem] = Field(default_factory=list)
    not_evaluated: list[NotEvaluatedFlag] = Field(default_factory=list)
    evidence_id: str = ""
    as_of: str = ""
    mode: str = "live"
    expired: bool = False


class ScenarioInputs(BaseModel):
    """User or agent parameters for a scenario simulation."""

    code: str
    move: float = Field(ge=-0.5, le=0.5, description="Underlying price move fraction [-0.5, 0.5]")
    days: int = Field(ge=0, description="Holding duration in days [0, days_left]")
    iv_shift: float = Field(ge=-15.0, le=15.0, description="Implied volatility shift in points [-15, +15]")


class CurvePoint(BaseModel):
    """Single point along a scenario PnL curve."""

    move: float
    display_move: str
    pnl_pct: float | None = None
    display_pnl_pct: str | None = None


class ScenarioCurve(BaseModel):
    """PnL curve for a specific holding horizon."""

    horizon_days: int
    display_horizon: str
    points: list[CurvePoint] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    """Outcome of a what-if scenario simulation."""

    inputs: ScenarioInputs
    entry_price: float
    display_entry_price: str
    exit_price: float
    display_exit_price: str
    pnl_pct: float
    display_pnl_pct: str
    breakeven_move: float | None = None
    display_breakeven_move: str | None = None
    curve: list[ScenarioCurve] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    evidence_id: str = ""


class NewsItem(BaseModel):
    """Structured news event item strictly constrained to 7-day recency window."""

    title: str = Field(max_length=200)
    url: str
    domain: str
    published_date: str | None = None
    retrieved_at: str
    event_type: str = "other"  # earnings|contract|dividend|director_dealing|corporate_action|regulatory|macro|other
    facts: list[str] = Field(default_factory=list)  # max 3 facts, each <= 160 chars
    stated_numbers: list[dict[str, str]] = Field(default_factory=list)
    corroboration_count: int = 1
    unconfirmed: bool = True
    extraction_method: str = "search_snippet"


class NearestWarrant(BaseModel):
    """Nearest-to-the-money warrant for stock summary."""

    code: str
    type: str
    strike: float
    display_strike: str
    distance_from_strike: float
    display_distance_from_strike: str
    bid: float | None = None
    display_bid: str | None = None
    ask: float | None = None
    display_ask: str | None = None
    days_to_expiry: int | None = None
    display_days_to_expiry: str | None = None
    effective_gearing: float | None = None
    display_effective_gearing: str | None = None


class StockSummary(BaseModel):
    """Aggregated market overview for an underlying stock."""

    ticker: str
    price: float | None = None
    display_price: str | None = None
    as_of: str = ""
    call_count: int = 0
    put_count: int = 0
    issuer_count: int = 0
    issuers: list[str] = Field(default_factory=list)
    min_expiry: str | None = None
    max_expiry: str | None = None
    median_spread_pct: float | None = None
    display_median_spread_pct: str | None = None
    median_flat_decay: float | None = None
    display_median_flat_decay: str | None = None
    flag_counts: dict[str, int] = Field(default_factory=dict)
    realized_vol_10d: float | None = None
    display_realized_vol_10d: str | None = None
    realized_vol_30d: float | None = None
    display_realized_vol_30d: str | None = None
    nearest_warrants: list[NearestWarrant] = Field(default_factory=list)
    evidence_id: str = ""


class Attribution(BaseModel):
    """Decomposition of warrant mid price change across underlying, time, vol, and residual."""

    code: str
    from_snapshot_id: int
    to_snapshot_id: int
    total_mid_change: float
    display_total_mid_change: str
    underlying_component: float
    display_underlying_component: str
    time_component: float
    display_time_component: str
    volatility_component: float
    display_volatility_component: str
    residual_component: float
    display_residual_component: str
    order: list[str] = Field(
        default_factory=lambda: ["underlying", "time", "volatility", "residual"]
    )
    evidence_id: str = ""


class RiskReport(BaseModel):
    """Deep risk report generated with multi-source evidence and counterpoints."""

    code: str
    summary: str
    cost_breakdown: dict[str, Any] = Field(default_factory=dict)
    what_must_go_right: list[str] = Field(default_factory=list)
    key_risks: list[dict[str, Any]] = Field(default_factory=list)
    counterpoints: list[str] = Field(default_factory=list)
    data_limits: list[str] = Field(default_factory=list)
    disclaimer: str = ""
    evidence_id: str = ""

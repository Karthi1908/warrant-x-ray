"""Bursa Malaysia warrant ratio convention and conversion logic.

In Bursa Malaysia, structured warrant ratios are quoted as X warrants per 1 underlying share
(e.g., ratio of 4.0 means 4 warrants control 1 underlying share).
Therefore:
shares_per_warrant = 1.0 / ratio
warrant_underlying_coverage = underlying_price / ratio
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RatioConvention:
    """Warrant conversion ratio parameters."""

    warrants_per_share: float
    shares_per_warrant: float


def parse_ratio_convention(ratio_raw: float) -> RatioConvention:
    """Parse and validate the warrant conversion ratio."""
    if ratio_raw <= 0.0:
        raise ValueError("Ratio must be positive")

    return RatioConvention(
        warrants_per_share=float(ratio_raw),
        shares_per_warrant=1.0 / float(ratio_raw),
    )


def shares_per_warrant(ratio_raw: float) -> float:
    """Return the fraction of an underlying share controlled by one warrant."""
    if ratio_raw <= 0.0:
        raise ValueError("Ratio must be positive")
    return 1.0 / float(ratio_raw)

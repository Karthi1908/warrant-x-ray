"""Realized volatility calculations from historical price series (T079).

Implements close-to-close annualized realized volatility:
- Daily log returns: r_i = ln(S_i / S_{i-1})
- Sample standard deviation of log returns
- Annualized using 252 trading days per year: sigma = s * sqrt(252) * 100
"""

from __future__ import annotations

import math
from typing import Sequence


def compute_log_returns(closes: Sequence[float]) -> list[float]:
    """Compute daily log returns: ln(P_t / P_{t-1})."""
    if len(closes) < 2:
        return []
    returns: list[float] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        curr = closes[i]
        if prev > 0 and curr > 0:
            returns.append(math.log(curr / prev))
    return returns


def compute_realized_volatility(
    closes: Sequence[float],
    annualization_factor: int = 252,
) -> float | None:
    """Compute annualized realized volatility in percentage points (e.g. 28.5%).

    Returns None if fewer than 3 price observations are available.
    """
    if len(closes) < 3:
        return None

    returns = compute_log_returns(closes)
    n = len(returns)
    if n < 2:
        return None

    mean_ret = sum(returns) / n
    variance = sum((r - mean_ret) ** 2 for r in returns) / (n - 1)
    daily_vol = math.sqrt(variance)
    annualized_vol = daily_vol * math.sqrt(annualization_factor) * 100.0

    return round(annualized_vol, 2)

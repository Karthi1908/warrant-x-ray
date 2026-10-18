"""Token and API pricing calculator.

Implements FR-CTRL-02, FR-CTRL-03:
- Calculates exact dollar costs for model token usage and Tavily search credits
  using config/prices.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

_DEFAULT_RATES: dict[str, dict[str, float]] = {
    "nemotron-3-nano": {"in": 0.15, "out": 0.60, "reasoning": 0.60},
    "nemotron-3-super": {"in": 0.80, "out": 2.40, "reasoning": 2.40},
    "nemotron-3-ultra": {"in": 2.50, "out": 10.00, "reasoning": 10.00},
}


def _load_pricing_rates() -> dict[str, dict[str, float]]:
    prices_file = Path("config/prices.yaml")
    if not prices_file.is_file():
        return _DEFAULT_RATES

    try:
        data = yaml.safe_load(prices_file.read_text(encoding="utf-8")) or {}
        models = data.get("models", {})
        rates = {}
        for m_name, m_info in models.items():
            rates[m_name] = {
                "in": float(m_info.get("input_price_per_million", 0.15)),
                "out": float(m_info.get("output_price_per_million", 0.60)),
                "reasoning": float(m_info.get("reasoning_price_per_million", 0.60)),
            }
        return rates or _DEFAULT_RATES
    except Exception:
        return _DEFAULT_RATES


_RATES = _load_pricing_rates()


def calculate_token_cost_usd(
    model: str,
    in_tokens: int,
    out_tokens: int,
    reasoning_tokens: int = 0,
) -> float:
    """Calculate USD cost for a given token usage breakdown."""
    model_key = model.lower()
    rates = None

    for k, v in _RATES.items():
        if k in model_key:
            rates = v
            break

    if not rates:
        rates = _DEFAULT_RATES.get("nemotron-3-super", {"in": 0.80, "out": 2.40, "reasoning": 2.40})

    in_cost = (in_tokens / 1_000_000.0) * rates["in"]
    out_cost = (out_tokens / 1_000_000.0) * rates["out"]
    reasoning_cost = (reasoning_tokens / 1_000_000.0) * rates["reasoning"]

    return round(in_cost + out_cost + reasoning_cost, 6)


def calculate_tavily_cost_usd(credits: int = 1) -> float:
    """Calculate USD cost for Tavily credits."""
    return round(credits * 0.005, 6)

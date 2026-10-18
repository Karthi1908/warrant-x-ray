"""Display formatting single source of truth and Evidence wrapper."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


def format_currency(
    val: float | None,
    decimals: int | None = None,
    prefix: str = "RM ",
) -> str | None:
    """Format currency values in Malaysian Ringgit (RM).

    If decimals is not specified, defaults to 3 decimal places for values < 1.0
    (standard Bursa warrant pricing) and 2 decimal places for values >= 1.0 (stocks).
    """
    if val is None or math.isnan(val) or math.isinf(val):
        return None
    if decimals is None:
        decimals = 3 if abs(val) < 1.0 else 2
    return f"{prefix}{val:.{decimals}f}"


def format_percent(
    val: float | None,
    decimals: int = 1,
    signed: bool = False,
) -> str | None:
    """Format decimal fractions as percentages (e.g. 0.052 -> 5.2%)."""
    if val is None or math.isnan(val) or math.isinf(val):
        return None
    pct = val * 100.0
    if signed and pct > 0:
        return f"+{pct:.{decimals}f}%"
    return f"{pct:.{decimals}f}%"


def format_points(
    val: float | None,
    decimals: int = 1,
    signed: bool = False,
) -> str | None:
    """Format volatility or index points (e.g. 2.5 -> 2.5 pts)."""
    if val is None or math.isnan(val) or math.isinf(val):
        return None
    if signed and val > 0:
        return f"+{val:.{decimals}f} pts"
    return f"{val:.{decimals}f} pts"


def format_ratio(
    val: float | None,
    decimals: int = 2,
) -> str | None:
    """Format gearing / multiplier values (e.g. 4.52 -> 4.52x)."""
    if val is None or math.isnan(val) or math.isinf(val):
        return None
    return f"{val:.{decimals}f}x"


def format_greek(
    val: float | None,
    decimals: int = 3,
) -> str | None:
    """Format option Greeks (delta, gamma, vega, theta)."""
    if val is None or math.isnan(val) or math.isinf(val):
        return None
    return f"{val:.{decimals}f}"


def format_int(val: int | float | None) -> str | None:
    """Format integers with comma separators (e.g. 1,250,000)."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return None
    return f"{int(val):,}"


def format_days(val: int | float | None) -> str | None:
    """Format day counts (e.g. 5 days, 1 day)."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return None
    ival = int(val)
    return "1 day" if ival == 1 else f"{ival} days"


_NUMBER_PATTERN = re.compile(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?|\.\d+%?")


def collect_display_strings(obj: Any) -> list[str]:
    """Recursively collect display strings and number tokens from an object or dictionary."""
    results: set[str] = set()

    def _traverse(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, (int, float)):
            if not (isinstance(item, float) and (math.isnan(item) or math.isinf(item))):
                results.add(str(item))
                if isinstance(item, float):
                    results.add(f"{item:.1f}")
                    results.add(f"{item:.2f}")
                    results.add(f"{item:.3f}")
        elif isinstance(item, str):
            results.add(item.strip())
            # Extract standalone numbers / percentages from strings
            for match in _NUMBER_PATTERN.finditer(item):
                results.add(match.group(0).replace(",", ""))
        elif isinstance(item, dict):
            for k, v in item.items():
                if k.startswith("display_") and isinstance(v, str):
                    results.add(v.strip())
                _traverse(v)
        elif isinstance(item, (list, tuple, set)):
            for v in item:
                _traverse(v)
        elif hasattr(item, "model_dump"):
            _traverse(item.model_dump())
        elif hasattr(item, "__dict__"):
            _traverse(item.__dict__)

    _traverse(obj)
    return sorted(list(results))


class Evidence(BaseModel):
    """Evidence record produced during a chat turn."""

    id: str = Field(description="Evidence identifier, e.g. E1, E2")
    turn_id: str | None = Field(default=None, description="Associated turn ID")
    kind: str = Field(
        description="Kind: snapshot, metrics, card, scenario, news, health, attribution, report"
    )
    source: str = Field(description="Source of evidence, e.g. bursa, quant_engine, tavily")
    as_of: str = Field(description="ISO 8601 UTC timestamp")
    summary: str = Field(description="Human-readable server-side summary")
    payload: dict[str, Any] = Field(description="Full structured data payload")
    allowlist: list[str] = Field(
        default_factory=list,
        description="List of verified display tokens and numbers for grounding verifier",
    )

    @classmethod
    def wrap(
        cls,
        evidence_id: str,
        kind: str,
        source: str,
        payload: dict[str, Any] | BaseModel,
        as_of: str | datetime | None = None,
        summary: str = "",
        turn_id: str | None = None,
    ) -> Evidence:
        """Construct an Evidence instance with automatic allowlist compilation."""
        if isinstance(payload, BaseModel):
            payload_dict = payload.model_dump()
        else:
            payload_dict = payload

        if as_of is None:
            as_of_str = datetime.now(timezone.utc).isoformat()
        elif isinstance(as_of, datetime):
            if as_of.tzinfo is None:
                as_of = as_of.replace(tzinfo=timezone.utc)
            as_of_str = as_of.isoformat()
        else:
            as_of_str = str(as_of)

        tokens = collect_display_strings(payload_dict)
        # Ensure evidence_id itself and [E#] format are in the allowlist
        tokens.append(evidence_id)
        tokens.append(f"[{evidence_id}]")

        if not summary:
            summary = f"{kind.capitalize()} evidence from {source}"

        return cls(
            id=evidence_id,
            turn_id=turn_id,
            kind=kind,
            source=source,
            as_of=as_of_str,
            summary=summary,
            payload=payload_dict,
            allowlist=sorted(list(set(tokens))),
        )

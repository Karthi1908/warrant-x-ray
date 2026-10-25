"""Warrant data normalization and sanitization (FR-DATA-03, FR-ERR-07, 10, 11).

Converts raw scraped/API data into normalized schema:
- Converts percentage strings ('42.5%') to float percentage points (42.5).
- Replaces sentinel strings ('-', 'N/A', '', 'null') with None.
- Validates crossed quotes (bid > ask) and marks row valid=False.
- Drops invalid or missing required fields safely.
- Deduplicates rows within the same snapshot, retaining the latest record.
"""

from __future__ import annotations

import math
from typing import Any

REQUIRED_FIELDS = {
    "code",
    "issuer",
    "type",
    "underlying_ticker",
    "expiry_date",
    "strike",
    "ratio_raw",
}

PLACEHOLDER_STRINGS = {"-", "n/a", "na", "null", "none", ""}


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if s.lower() in PLACEHOLDER_STRINGS:
        return None
    return s


def _clean_float(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    s = str(val).strip()
    if s.lower() in PLACEHOLDER_STRINGS:
        return None
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        f = float(s)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except ValueError:
        return None


def _clean_int(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val) if not (math.isnan(val) or math.isinf(val)) else None
    s = str(val).strip()
    if s.lower() in PLACEHOLDER_STRINGS:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def normalize_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a single warrant row dictionary.

    Returns None if missing required identification fields.
    """
    for field in REQUIRED_FIELDS:
        if field not in row or row[field] is None:
            return None
        if isinstance(row[field], str) and row[field].strip().lower() in PLACEHOLDER_STRINGS:
            return None

    code = str(row["code"]).strip().upper()
    issuer = str(row["issuer"]).strip().upper()
    w_type = str(row["type"]).strip().lower()
    ticker = str(row["underlying_ticker"]).strip().upper()
    expiry_date = str(row["expiry_date"]).strip()

    strike = _clean_float(row["strike"])
    ratio_raw = _clean_float(row["ratio_raw"])

    if strike is None or strike <= 0 or ratio_raw is None or ratio_raw <= 0:
        return None

    norm: dict[str, Any] = {
        "code": code,
        "issuer": issuer,
        "type": w_type,
        "underlying_ticker": ticker,
        "expiry_date": expiry_date,
        "strike": strike,
        "ratio_raw": ratio_raw,
        "underlying_bid": _clean_float(row.get("underlying_bid")),
        "bid": _clean_float(row.get("bid")),
        "ask": _clean_float(row.get("ask")),
        "bid_volume": _clean_int(row.get("bid_volume")),
        "ask_volume": _clean_int(row.get("ask_volume")),
        "traded_volume": _clean_int(row.get("traded_volume")),
        "last_price": _clean_float(row.get("last_price")),
        "last_time": _clean_str(row.get("last_time")),
        "issuer_iv": _clean_float(row.get("issuer_iv")),
        "issuer_eg": _clean_float(row.get("issuer_eg")),
        "issuer_delta": _clean_float(row.get("issuer_delta")),
        "issuer_premium": _clean_float(row.get("issuer_premium")),
        "issuer_theta_raw": _clean_float(row.get("issuer_theta_raw")),
        "sensitivity_ticks": _clean_float(row.get("sensitivity_ticks")),
        "moneyness": _clean_float(row.get("moneyness")),
        "indicators": row.get("indicators") if isinstance(row.get("indicators"), dict) else {},
        "valid": bool(row.get("valid", True)),
        "quality_flags": list(row.get("quality_flags", [])),
    }

    # Crossed quotes check
    if norm["bid"] is not None and norm["ask"] is not None:
        if norm["bid"] > norm["ask"]:
            norm["valid"] = False
            if "crossed_quotes" not in norm["quality_flags"]:
                norm["quality_flags"].append("crossed_quotes")

    return norm


def normalize_snapshot_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a batch of rows and deduplicate by code, retaining the latest."""
    dedup: dict[str, dict[str, Any]] = {}
    for r in rows:
        norm = normalize_row(r)
        if norm is not None:
            dedup[norm["code"]] = norm
    return list(dedup.values())

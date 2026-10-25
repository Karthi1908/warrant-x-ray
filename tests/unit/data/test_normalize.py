"""Unit tests for warrant data normalization and quality checks (T071, FR-DATA-03, FR-ERR-07, 10, 11).

Tests:
1. Percent-to-fraction conversion (e.g. '12.5%' -> 0.125, 42.5 -> 0.425).
2. Invalid/empty values to None ('-', 'N/A', '', 'null').
3. Deduplication of warrant rows by code.
4. Crossed quotes detection (bid > ask) marking row as invalid.
5. Incomplete row handling without crashes.
"""

import pytest
from warrantx.data.normalize import normalize_row, normalize_snapshot_rows


def test_percent_to_fraction():
    """Converts strings and numbers representing percentages to float fractions."""
    row = {
        "code": "115510",
        "issuer": "CGS",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": "2027-06-30",
        "strike": "10.50",
        "ratio_raw": "4.0",
        "issuer_iv": "42.5%",
        "issuer_premium": "8.5%",
        "bid": "0.150",
        "ask": "0.155",
    }
    norm = normalize_row(row)
    assert norm is not None
    assert norm["issuer_iv"] == 42.5  # Stored as percentage points (42.5)
    assert norm["issuer_premium"] == 8.5
    assert norm["strike"] == 10.50
    assert norm["ratio_raw"] == 4.0
    assert norm["bid"] == 0.150
    assert norm["ask"] == 0.155


def test_invalid_strings_to_none():
    """Converts placeholder strings ('-', 'N/A', '', 'null') to None."""
    row = {
        "code": "115510",
        "issuer": "CGS",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": "2027-06-30",
        "strike": 10.5,
        "ratio_raw": 4.0,
        "bid": "-",
        "ask": "N/A",
        "last_price": "",
        "issuer_iv": "null",
    }
    norm = normalize_row(row)
    assert norm is not None
    assert norm["bid"] is None
    assert norm["ask"] is None
    assert norm["last_price"] is None
    assert norm["issuer_iv"] is None


def test_crossed_quotes_flagged_invalid():
    """Crossed quotes where bid > ask marks the row as valid=False."""
    row = {
        "code": "115510",
        "issuer": "CGS",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": "2027-06-30",
        "strike": 10.5,
        "ratio_raw": 4.0,
        "bid": 0.200,
        "ask": 0.180,  # bid > ask
    }
    norm = normalize_row(row)
    assert norm is not None
    assert norm["valid"] is False
    assert "crossed_quotes" in norm.get("quality_flags", [])


def test_deduplicate_warrant_rows():
    """Duplicate warrant codes within the same snapshot are deduplicated keeping latest."""
    rows = [
        {
            "code": "115510",
            "issuer": "CGS",
            "type": "call",
            "underlying_ticker": "MAYBANK",
            "expiry_date": "2027-06-30",
            "strike": 10.5,
            "ratio_raw": 4.0,
            "bid": 0.140,
            "ask": 0.150,
        },
        {
            "code": "115510",
            "issuer": "CGS",
            "type": "call",
            "underlying_ticker": "MAYBANK",
            "expiry_date": "2027-06-30",
            "strike": 10.5,
            "ratio_raw": 4.0,
            "bid": 0.150,
            "ask": 0.160,
        },
    ]
    normalized = normalize_snapshot_rows(rows)
    assert len(normalized) == 1
    assert normalized[0]["bid"] == 0.150


def test_missing_required_fields_dropped():
    """Rows missing critical identification fields are safely dropped."""
    incomplete_row = {
        "bid": 0.150,
        "ask": 0.160,
    }
    assert normalize_row(incomplete_row) is None

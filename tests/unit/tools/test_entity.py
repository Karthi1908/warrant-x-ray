"""Unit tests for entity resolution tool.

Implements T049 (FR-NAME-01 to 04, AC-06).
"""

import pytest

from warrantx.tools.entity import EntityMatchResult, resolve_entity

UNDERLYINGS_SAMPLE = [
    {"ticker": "MAYBANK", "code": "1155", "name": "Malayan Banking Berhad"},
    {"ticker": "TENAGA", "code": "5347", "name": "Tenaga Nasional Berhad"},
    {"ticker": "PBBANK", "code": "1295", "name": "Public Bank Berhad"},
    {"ticker": "GENTING", "code": "3182", "name": "Genting Berhad"},
    {"ticker": "GENM", "code": "4715", "name": "Genting Malaysia Berhad"},
    {"ticker": "YTLPOWR", "code": "6742", "name": "YTL Power International Berhad"},
]


def test_resolve_exact_ticker_and_code():
    """Verify exact matching by ticker symbol and Bursa numeric stock code."""
    res = resolve_entity("MAYBANK", candidates=UNDERLYINGS_SAMPLE)
    assert res.status == "exact"
    assert res.matched_ticker == "MAYBANK"

    res_code = resolve_entity("1155", candidates=UNDERLYINGS_SAMPLE)
    assert res_code.status == "exact"
    assert res_code.matched_ticker == "MAYBANK"


def test_resolve_case_and_whitespace_insensitivity():
    """Verify case trimming and whitespace tolerance."""
    res = resolve_entity("  maybank  ", candidates=UNDERLYINGS_SAMPLE)
    assert res.status == "exact"
    assert res.matched_ticker == "MAYBANK"


def test_resolve_fuzzy_name():
    """Verify rapidfuzz matching for typos and partial company names."""
    res = resolve_entity("Maybnk", candidates=UNDERLYINGS_SAMPLE)
    assert res.status in ("exact", "fuzzy")
    assert res.matched_ticker == "MAYBANK"

    res2 = resolve_entity("Tenaga Nas", candidates=UNDERLYINGS_SAMPLE)
    assert res2.status in ("exact", "fuzzy")
    assert res2.matched_ticker == "TENAGA"


def test_resolve_ambiguity():
    """Verify ambiguous inputs return an ambiguity status with plausible choices."""
    res = resolve_entity("Genting", candidates=UNDERLYINGS_SAMPLE)
    # Both GENTING and GENM (Genting Malaysia) are close matches
    assert res.status in ("ambiguous", "fuzzy")
    if res.status == "ambiguous":
        tickers = [c["ticker"] for c in res.candidates]
        assert "GENTING" in tickers
        assert "GENM" in tickers


def test_resolve_no_match_returns_suggestions():
    """Verify completely unknown company returns suggestions without crashing."""
    res = resolve_entity("Apple Inc", candidates=UNDERLYINGS_SAMPLE)
    assert res.status == "not_found"
    assert len(res.suggestions) <= 3

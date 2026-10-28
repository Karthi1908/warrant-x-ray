"""Unit tests for smart underlying ticker resolution and intent classification."""

import pytest
from unittest.mock import AsyncMock

from warrantx.chat.intent import classify_intent, resolve_underlying_ticker
from warrantx.data.repo import Underlying


SAMPLE_UNDERLYINGS = [
    Underlying(ticker="RHBBANK", code="1066", name="RHB BANK BHD"),
    Underlying(ticker="MAYBANK", code="1155", name="MAYBANK BHD"),
    Underlying(ticker="PBBANK", code="1295", name="PUBLIC BANK BHD"),
    Underlying(ticker="HLBANK", code="5819", name="HONG LEONG BANK"),
    Underlying(ticker="AMBANK", code="1015", name="AMMB HLDGS BHD"),
    Underlying(ticker="CIMB", code="1023", name="CIMB GRP BHD"),
    Underlying(ticker="TENAGA", code="5347", name="TENAGA NASIONAL"),
    Underlying(ticker="YTL", code="4677", name="YTL CORPORATION"),
    Underlying(ticker="YTLPOWR", code="6742", name="YTL POWER"),
    Underlying(ticker="TOPGLOV", code="7113", name="TOP GLOVE CORP"),
    Underlying(ticker="PMETAL", code="8869", name="PRESS METAL"),
    Underlying(ticker="BURSA", code="1818", name="BURSA MALAYSIA"),
    Underlying(ticker="MAXIS", code="6012", name="MAXIS BERHAD"),
    Underlying(ticker="HI", code="0328", name="HI MOBILITY"),
]


@pytest.mark.parametrize(
    "query,expected_ticker",
    [
        ("RHB", "RHBBANK"),
        ("RHB BANK", "RHBBANK"),
        ("rhb", "RHBBANK"),
        ("rhb bank", "RHBBANK"),
        ("RHBBANK", "RHBBANK"),
        ("warrants on rhb", "RHBBANK"),
        ("show me rhb bank warrants", "RHBBANK"),
        ("what is the best warrant for rhb bank?", "RHBBANK"),
        ("Maybank", "MAYBANK"),
        ("may bank", "MAYBANK"),
        ("Public Bank", "PBBANK"),
        ("public bank", "PBBANK"),
        ("PBB", "PBBANK"),
        ("TNB", "TENAGA"),
        ("Tenaga", "TENAGA"),
        ("YTL Power", "YTLPOWR"),
        ("ytl power", "YTLPOWR"),
        ("ytl", "YTL"),
        ("Top Glove", "TOPGLOV"),
        ("Press Metal", "PMETAL"),
        ("CIMB", "CIMB"),
        ("cimb bank", "CIMB"),
        ("Hong Leong Bank", "HLBANK"),
        ("hong leong", "HLBANK"),
        ("AmBank", "AMBANK"),
        ("am bank", "AMBANK"),
        ("Bursa Malaysia", "BURSA"),
        ("Maxis", "MAXIS"),
        ("I am looking for call warrants", None),
        ("hi there what is available", None),
    ],
)
def test_resolve_underlying_ticker(query: str, expected_ticker: str | None):
    """resolve_underlying_ticker identifies stock even if user enters informal abbreviations."""
    resolved = resolve_underlying_ticker(query, SAMPLE_UNDERLYINGS)
    assert resolved == expected_ticker


@pytest.mark.asyncio
async def test_classify_intent_resolves_rhb_ticker():
    """classify_intent correctly sets ticker to RHBBANK when user enters only RHB or RHB BANK."""
    repo = AsyncMock()
    repo.get_warrant = AsyncMock(return_value=None)
    repo.list_underlyings = AsyncMock(return_value=SAMPLE_UNDERLYINGS)

    # 1. Plain "RHB"
    res1 = await classify_intent("warrants on RHB", repo=repo)
    assert res1.ticker == "RHBBANK"
    assert res1.intent == "explain_warrant"

    # 2. "RHB BANK"
    res2 = await classify_intent("tell me about rhb bank", repo=repo)
    assert res2.ticker == "RHBBANK"
    assert res2.intent == "explain_warrant"

    # 3. News intent on RHB
    res3 = await classify_intent("latest news on rhb", repo=repo)
    assert res3.ticker == "RHBBANK"
    assert res3.intent == "news"

    # 4. Compare RHB
    res4 = await classify_intent("compare rhb vs maybank", repo=repo)
    assert res4.ticker in ("RHBBANK", "MAYBANK")
    assert res4.intent == "compare"

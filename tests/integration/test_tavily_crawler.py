"""Integration tests for Tavily crawler client and screener fallback (T117, FR-007, FR-020)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from warrantx.data.tavily_crawler import TavilyWarrantCrawler
from warrantx.news.tavily_gateway import TavilyBudgetExhaustedError, TavilyError


@pytest.mark.asyncio
async def test_tavily_crawler_success(test_repo):
    crawler = TavilyWarrantCrawler(
        api_key="test-key",
        repo=test_repo,
        crawl_credit_limit=50,
    )

    mock_html = """
    <table>
        <tr><th>Code</th><th>Issuer</th><th>Type</th><th>Underlying</th><th>Strike</th><th>Ratio</th><th>Expiry</th><th>Bid</th><th>Ask</th><th>Underlying Price</th></tr>
        <tr><td>115510</td><td>CGS</td><td>Call</td><td>MAYBANK</td><td>10.50</td><td>4.0</td><td>2027-06-30</td><td>0.150</td><td>0.155</td><td>10.20</td></tr>
    </table>
    """

    with patch.object(crawler, "_fetch_crawled_html", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_html
        rows = await crawler.crawl_warrants()

        assert len(rows) == 1
        assert rows[0]["code"] == "115510"
        assert rows[0]["underlying_ticker"] == "MAYBANK"

        # Check crawl credit recorded in budget
        credits_used = await crawler.get_daily_crawl_credits()
        assert credits_used == 1


@pytest.mark.asyncio
async def test_tavily_crawler_budget_exhaustion(test_repo):
    crawler = TavilyWarrantCrawler(
        api_key="test-key",
        repo=test_repo,
        crawl_credit_limit=2,
    )

    # Artificially record 2 credits to exhaust limit
    from warrantx.llm.usage import get_malaysia_today
    today = get_malaysia_today()
    await test_repo.record_budget_spend(day=today, kind="tavily_crawl_credits", amount=2.0)

    with pytest.raises(TavilyBudgetExhaustedError):
        await crawler.crawl_warrants()


@pytest.mark.asyncio
async def test_tavily_crawler_fallback_to_screener(test_repo):
    crawler = TavilyWarrantCrawler(
        api_key="test-key",
        repo=test_repo,
        crawl_credit_limit=50,
    )

    with patch.object(crawler, "_fetch_crawled_html", side_effect=TavilyError("Network failed")):
        with patch("warrantx.data.source_client.fetch_snapshot", new_callable=AsyncMock) as mock_screener:
            mock_screener.return_value = [
                {
                    "code": "51881C",
                    "issuer": "CGS",
                    "type": "call",
                    "underlying_ticker": "MAYBANK",
                    "expiry_date": "2026-12-31",
                    "strike": 10.50,
                    "ratio_raw": 4.0,
                    "underlying_bid": 10.20,
                    "bid": 0.080,
                    "ask": 0.090,
                }
            ]

            rows, source = await crawler.collect_with_fallback()
            assert len(rows) == 1
            assert rows[0]["code"] == "51881C"
            assert source == "direct_screener"

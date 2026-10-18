"""Integration tests for TavilyGateway (T084, FR-NEWS).

Tests:
1. Search query returns results strictly constrained to 7-day window.
2. Extract returns content for up to 3 URLs.
3. Empty extract returns empty list gracefully.
4. Usage-limit / budget exhaustion errors are caught and mapped to standard errors.
"""

from unittest.mock import AsyncMock, patch
import pytest

from warrantx.news.tavily_gateway import (
    TavilyGateway,
    TavilyError,
    TavilyBudgetExhaustedError,
)


@pytest.fixture
def mock_tavily_search_response():
    return {
        "results": [
            {
                "title": "Maybank posts record quarterly earnings",
                "url": "https://www.thestar.com.my/business/2026/10/12/maybank-record",
                "content": "Malayan Banking Bhd reported a surge in quarterly net profit...",
                "published_date": "2026-10-12T08:00:00Z",
                "score": 0.95,
            },
            {
                "title": "Maybank expands digital banking initiatives",
                "url": "https://theedgemalaysia.com/article/maybank-digital",
                "content": "The bank announced strategic investments in cloud systems...",
                "published_date": "2026-10-13T10:00:00Z",
                "score": 0.88,
            },
        ]
    }


@pytest.mark.asyncio
async def test_tavily_search_success(mock_tavily_search_response):
    """Search queries Tavily news topic with fixed 7-day recency window."""
    with patch("warrantx.news.tavily_gateway.AsyncTavilyClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.search = AsyncMock(return_value=mock_tavily_search_response)
        mock_client_cls.return_value = mock_instance

        gateway = TavilyGateway(api_key="tvly-testkey")
        results = await gateway.search_news("MAYBANK", max_results=5)

        assert len(results) == 2
        assert results[0]["title"] == "Maybank posts record quarterly earnings"
        assert results[0]["url"] == "https://www.thestar.com.my/business/2026/10/12/maybank-record"
        assert results[0]["domain"] == "thestar.com.my"

        # Verify strict 7-day recency window was passed
        mock_instance.search.assert_called_once()
        _, kwargs = mock_instance.search.call_args
        assert kwargs.get("days") == 7
        assert kwargs.get("topic") == "news"


@pytest.mark.asyncio
async def test_tavily_extract_max_3_urls():
    """Extract processes at most 3 URLs even if more are requested."""
    with patch("warrantx.news.tavily_gateway.AsyncTavilyClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.extract = AsyncMock(
            return_value={
                "results": [
                    {"url": "https://site1.com", "raw_content": "Content 1"},
                    {"url": "https://site2.com", "raw_content": "Content 2"},
                    {"url": "https://site3.com", "raw_content": "Content 3"},
                ]
            }
        )
        mock_client_cls.return_value = mock_instance

        gateway = TavilyGateway(api_key="tvly-testkey")
        urls = [
            "https://site1.com",
            "https://site2.com",
            "https://site3.com",
            "https://site4.com",
            "https://site5.com",
        ]
        results = await gateway.extract(urls)

        assert len(results) == 3
        mock_instance.extract.assert_called_once()
        _, kwargs = mock_instance.extract.call_args
        assert len(kwargs.get("urls", [])) == 3


@pytest.mark.asyncio
async def test_tavily_extract_empty():
    """Empty URL list or empty extract returns empty list without error."""
    with patch("warrantx.news.tavily_gateway.AsyncTavilyClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.extract = AsyncMock(return_value={"results": []})
        mock_client_cls.return_value = mock_instance

        gateway = TavilyGateway(api_key="tvly-testkey")
        results = await gateway.extract([])
        assert results == []


@pytest.mark.asyncio
async def test_tavily_usage_limit_error():
    """Usage-limit/budget errors from Tavily raise TavilyBudgetExhaustedError."""
    with patch("warrantx.news.tavily_gateway.AsyncTavilyClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.search = AsyncMock(side_effect=Exception("Usage limit exceeded"))
        mock_client_cls.return_value = mock_instance

        gateway = TavilyGateway(api_key="tvly-testkey")
        with pytest.raises(TavilyBudgetExhaustedError):
            await gateway.search_news("MAYBANK")

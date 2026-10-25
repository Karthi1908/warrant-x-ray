"""Tavily warrant web crawler client with deterministic parsing and fallback (T119, FR-007, FR-020).

Constitution Principle I & VII:
- 0% LLM extraction and 0% LLM math.
- Crawled HTML is parsed deterministically using BeautifulSoup.
- Budget capped at 50 credits/day, tracked under kind="tavily_crawl_credits".
- Falls back to direct screener on crawl failure or budget exhaustion.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from tavily import AsyncTavilyClient

from warrantx.config import get_settings
from warrantx.data.html_parser import parse_warrant_table_html
from warrantx.llm.usage import get_malaysia_today
from warrantx.news.tavily_gateway import TavilyBudgetExhaustedError, TavilyError

if TYPE_CHECKING:
    from warrantx.data.repo import AsyncRepository

logger = logging.getLogger(__name__)

DEFAULT_CRAWL_TARGET = "https://www.malaysiawarrants.com.my/tools/screener"


class TavilyWarrantCrawler:
    """Crawler client using Tavily extract to retrieve Bursa warrant screener pages."""

    def __init__(
        self,
        api_key: str | None = None,
        repo: AsyncRepository | None = None,
        crawl_credit_limit: int = 50,
        target_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.tavily_api_key or os.environ.get("WX_TAVILY_API_KEY", "")
        self.repo = repo
        self.crawl_credit_limit = crawl_credit_limit or settings.tavily_crawl_credit_limit
        self.target_url = target_url or settings.tavily_crawl_url or DEFAULT_CRAWL_TARGET
        self._client: AsyncTavilyClient | None = None

    @property
    def client(self) -> AsyncTavilyClient:
        if self._client is None:
            self._client = AsyncTavilyClient(api_key=self.api_key)
        return self._client

    async def _fetch_crawled_html(self, url: str | None = None) -> str:
        """Fetch raw page HTML via Tavily extract."""
        target = url or self.target_url
        if not self.api_key:
            raise TavilyError("Missing Tavily API key for warrant crawling")

        try:
            response = await self.client.extract(urls=[target])
        except Exception as err:
            err_msg = str(err).lower()
            if "usage limit" in err_msg or "budget" in err_msg or "quota" in err_msg or "credit" in err_msg:
                raise TavilyBudgetExhaustedError(str(err)) from err
            raise TavilyError(f"Tavily crawl extract failed: {err}") from err

        results = response.get("results", []) if isinstance(response, dict) else []
        if not results:
            return ""

        first_res = results[0]
        # raw_content contains full page HTML/text; fallback to content
        return first_res.get("raw_content") or first_res.get("content") or ""

    async def get_daily_crawl_credits(self, day: str | None = None) -> int:
        """Get the number of Tavily crawl credits spent today."""
        if self.repo is None:
            return 0
        target_day = day or get_malaysia_today()
        spent = await self.repo.get_budget_usage(day=target_day, kind="tavily_crawl_credits")
        return int(spent)

    async def crawl_warrants(self) -> list[dict[str, Any]]:
        """Crawl warrant market data deterministically within daily 50-credit ceiling."""
        today = get_malaysia_today()
        current_credits = await self.get_daily_crawl_credits(today)

        if current_credits >= self.crawl_credit_limit:
            raise TavilyBudgetExhaustedError(
                f"Daily Tavily crawl credit ceiling ({self.crawl_credit_limit}) reached ({current_credits} used today)"
            )

        html = await self._fetch_crawled_html()
        rows = parse_warrant_table_html(html)

        if self.repo is not None:
            await self.repo.record_budget_spend(
                day=today, kind="tavily_crawl_credits", amount=1.0
            )

        return rows

    async def collect_with_fallback(self) -> tuple[list[dict[str, Any]], str]:
        """Attempt Tavily crawl first, falling back to direct screener on error or exhaustion."""
        try:
            rows = await self.crawl_warrants()
            if rows:
                return rows, "tavily_crawl"
            logger.warning("Tavily crawl returned 0 rows, falling back to direct screener")
        except TavilyBudgetExhaustedError as err:
            logger.warning("Tavily crawl budget exhausted (%s), falling back to direct screener", err)
        except Exception as err:
            logger.warning("Tavily crawl failed (%s), falling back to direct screener", err)

        # Direct screener fallback
        from warrantx.data.source_client import fetch_snapshot

        fallback_rows = await fetch_snapshot()
        return fallback_rows, "direct_screener"

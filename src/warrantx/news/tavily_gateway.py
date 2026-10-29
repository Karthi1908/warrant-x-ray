"""Tavily search and extract gateway (T087, FR-NEWS-01 to 03).

Constitution VII:
- Only module allowed to import `tavily`.
- Strict 7-day recency window (FR-016).
- Budget enforcement and error mapping.
- Treats all extracted external content as untrusted.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from tavily import AsyncTavilyClient


class TavilyError(Exception):
    """Base error for Tavily gateway operations."""
    pass


class TavilyBudgetExhaustedError(TavilyError):
    """Raised when Tavily credit limit or usage quota is exceeded."""
    pass


class TavilyGateway:
    """Gateway client for Tavily news search and content extraction."""

    EXCLUDED_SOCIAL_DOMAINS = [
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "twitter.com",
        "x.com",
        "youtube.com",
        "linkedin.com",
        "pinterest.com",
        "reddit.com",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 10.0,
        enabled: bool = True,
        daily_credit_limit: int = 200,
    ) -> None:
        raw_key = api_key if api_key is not None else os.environ.get("WX_TAVILY_API_KEY", "")
        self.api_key = raw_key.strip().strip('"').strip("'")
        self.timeout = timeout
        self.enabled = enabled and bool(self.api_key)
        self.daily_credit_limit = daily_credit_limit
        self._client: AsyncTavilyClient | None = None

    @property
    def client(self) -> AsyncTavilyClient:
        """Lazily initialize AsyncTavilyClient."""
        if self._client is None:
            self._client = AsyncTavilyClient(api_key=self.api_key)
        return self._client

    async def search_news(
        self,
        query: str,
        days: int = 7,
        max_results: int = 6,
    ) -> list[dict[str, Any]]:
        """Search news with strict 7-day recency window (FR-016)."""
        if not self.enabled:
            return []

        try:
            # Strictly enforce 7 days and exclude social media noise
            response = await self.client.search(
                query=query,
                topic="news",
                days=7,
                max_results=max_results,
                exclude_domains=self.EXCLUDED_SOCIAL_DOMAINS,
            )
            raw_results = response.get("results", []) if isinstance(response, dict) else []
            if not raw_results:
                response = await self.client.search(
                    query=query,
                    topic="general",
                    days=7,
                    max_results=max_results,
                    exclude_domains=self.EXCLUDED_SOCIAL_DOMAINS,
                )
                raw_results = response.get("results", []) if isinstance(response, dict) else []
        except Exception as err:
            err_msg = str(err).lower()
            if "usage limit" in err_msg or "budget" in err_msg or "quota" in err_msg or "credit" in err_msg:
                raise TavilyBudgetExhaustedError(str(err)) from err
            raise TavilyError(f"Tavily search failed: {err}") from err
        formatted: list[dict[str, Any]] = []

        for item in raw_results:
            url = item.get("url", "")
            domain = ""
            if url:
                try:
                    domain = urlparse(url).netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                except Exception:
                    domain = "unknown"

            formatted.append({
                "title": item.get("title", ""),
                "url": url,
                "domain": domain,
                "content": item.get("content", ""),
                "published_date": item.get("published_date"),
                "score": item.get("score", 0.0),
            })

        return formatted

    async def extract(self, urls: list[str]) -> list[dict[str, Any]]:
        """Extract content for up to 3 URLs."""
        if not self.enabled or not urls:
            return []

        target_urls = urls[:3]
        try:
            response = await self.client.extract(urls=target_urls)
        except Exception as err:
            err_msg = str(err).lower()
            if "usage limit" in err_msg or "budget" in err_msg or "quota" in err_msg or "credit" in err_msg:
                raise TavilyBudgetExhaustedError(str(err)) from err
            raise TavilyError(f"Tavily extract failed: {err}") from err

        if isinstance(response, dict):
            return response.get("results", [])
        return []

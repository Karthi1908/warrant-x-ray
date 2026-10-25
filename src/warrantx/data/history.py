"""Historical price provider and realized volatility lookup for underlyings (T079).

Provides:
- Historical close series from SQLite price_history table.
- Yahoo Finance `.KL` ticker lookup with fallback.
- Realized volatility calculation over standard windows (20-day, 30-day).
"""

from __future__ import annotations

import httpx

from warrantx.data.repo import AsyncRepository
from warrantx.quant.vol import compute_realized_volatility


class HistoryProvider:
    """Provides historical underlying stock prices and realized volatility metrics."""

    def __init__(self, repo: AsyncRepository, enable_yahoo_fallback: bool = False) -> None:
        self.repo = repo
        self.enable_yahoo_fallback = enable_yahoo_fallback

    async def get_recent_closes(self, ticker: str, limit: int = 35) -> list[float]:
        """Fetch chronological close prices for a ticker."""
        clean_ticker = ticker.strip().upper()
        closes = await self.repo.get_recent_closes(clean_ticker, limit=limit)
        if closes:
            return closes

        if self.enable_yahoo_fallback:
            yahoo_closes = await self._fetch_yahoo_closes(clean_ticker, limit=limit)
            if yahoo_closes:
                return yahoo_closes

        return []

    async def _fetch_yahoo_closes(self, ticker: str, limit: int = 35) -> list[float]:
        """Fetch daily closes from Yahoo Finance with .KL suffix."""
        yahoo_symbol = f"{ticker}.KL" if not ticker.endswith(".KL") else ticker
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?range=3mo&interval=1d"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"User-Agent": "WarrantXRay/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        quote = result[0].get("indicators", {}).get("quote", [{}])[0]
                        closes = [c for c in quote.get("close", []) if c is not None and c > 0]
                        return closes[-limit:]
        except Exception:
            pass
        return []

    async def get_realized_volatility(self, ticker: str, window: int = 20) -> float | None:
        """Compute annualized realized volatility for a ticker over a given window."""
        closes = await self.get_recent_closes(ticker, limit=window + 5)
        if len(closes) < 3:
            return None
        return compute_realized_volatility(closes[-window:])

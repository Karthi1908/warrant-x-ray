"""News cache, persistent replay, and service orchestration (T089, Constitution IX, FR-NEWS-01..09).

Coordinates:
- 30-minute short-term SQLite cache (news_cache table).
- Persistent replay storage (stored_news_sets table) for offline resilience.
- Live Tavily search gateway with strict 7-day filter, sanitization, and multi-domain corroboration.
- Deterministic fallback to synthetic illustrative fixtures in tests/fixtures/news/.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from warrantx.api.logging import get_logger
from warrantx.data.repo import AsyncRepository
from warrantx.news.corroborate import corroborate_news, deduplicate_news
from warrantx.news.structure import filter_7day_window, sanitize_news_item
from warrantx.news.tavily_gateway import TavilyGateway
from warrantx.tools.models import NewsItem

logger = get_logger("warrantx.news")

TICKER_COMPANY_NAMES: dict[str, str] = {
    "MAYBANK": "Maybank Malayan Banking Berhad",
    "TENAGA": "Tenaga Nasional Berhad TNB",
    "PBBANK": "Public Bank Berhad",
    "CIMB": "CIMB Group Holdings Berhad",
    "IHH": "IHH Healthcare Berhad",
    "CELCOMDIGI": "CelcomDigi Berhad",
    "PCHEM": "Petronas Chemicals Group Berhad",
    "INARI": "Inari Amertron Berhad",
    "YTL": "YTL Corporation Berhad",
    "YTLPOWR": "YTL Power International Berhad",
    "GAMUDA": "Gamuda Berhad",
    "SUNWAY": "Sunway Berhad",
    "BURSA": "Bursa Malaysia Berhad",
    "GENTING": "Genting Berhad",
    "GENM": "Genting Malaysia Berhad",
    "AXIATA": "Axiata Group Berhad",
    "MAXIS": "Maxis Berhad",
    "TELEKOM": "Telekom Malaysia Berhad TM",
    "MISC": "MISC Berhad",
    "SIME": "Sime Darby Berhad",
    "SDG": "SD Guthrie Berhad",
    "SIMEPROP": "Sime Darby Property Berhad",
    "IOICORP": "IOI Corporation Berhad",
    "KLK": "Kuala Lumpur Kepong Berhad",
    "RHBBANK": "RHB Bank Berhad",
    "HLBANK": "Hong Leong Bank Berhad",
    "AMBANK": "AMMB Holdings AmBank",
    "PMETAL": "Press Metal Aluminium Holdings Berhad",
    "PETGAS": "Petronas Gas Berhad",
    "PETDAG": "Petronas Dagangan Berhad",
    "MRDIY": "MR D.I.Y. Group Malaysia",
    "NESTLE": "Nestle Malaysia Berhad",
    "QL": "QL Resources Berhad",
    "DIALOG": "Dialog Group Berhad",
    "MYEG": "MY E.G. Services Berhad Zetrix",
    "TOPGLOV": "Top Glove Corporation Berhad",
    "HARTALEGA": "Hartalega Holdings Berhad",
    "KOSSAN": "Kossan Rubber Industries",
    "SPSETIA": "S P Setia Berhad",
    "UEMS": "UEM Sunrise Berhad",
    "MAHB": "Malaysia Airports Holdings Berhad",
    "CAPITALA": "Capital A AirAsia",
    "AAX": "AirAsia X Berhad",
}

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures" / "news" / "sample_news.json"


class NewsService:
    """Orchestrates news fetching, caching, corroboration, and offline replay."""

    def __init__(
        self,
        repo: AsyncRepository,
        mode: str = "sample",
        tavily_gateway: TavilyGateway | None = None,
    ) -> None:
        self.repo = repo
        self.tavily_gateway = tavily_gateway
        norm_mode = mode.lower()
        if norm_mode != "replay" and tavily_gateway is not None and getattr(tavily_gateway, "enabled", False):
            self.mode = "live"
        else:
            self.mode = norm_mode
        self._fixtures: dict[str, list[dict[str, Any]]] | None = None

    def _load_fixtures(self) -> dict[str, list[dict[str, Any]]]:
        if self._fixtures is not None:
            return self._fixtures
        if FIXTURES_PATH.exists():
            try:
                with open(FIXTURES_PATH, encoding="utf-8") as f:
                    self._fixtures = json.load(f)
                    return self._fixtures
            except Exception:
                pass
        self._fixtures = {}
        return self._fixtures

    def _get_fallback_fixtures(self, ticker: str) -> list[NewsItem]:
        fixtures = self._load_fixtures()
        normalized_ticker = ticker.upper().strip()
        raw_items = fixtures.get(normalized_ticker)
        now_iso = datetime.now(timezone.utc).isoformat()

        if raw_items:
            items: list[NewsItem] = []
            for raw in raw_items:
                raw_copy = dict(raw)
                if not raw_copy.get("retrieved_at"):
                    raw_copy["retrieved_at"] = now_iso
                items.append(NewsItem(**raw_copy))
            return items

        # Generic illustrative fallback if ticker not in fixture file
        return [
            NewsItem(
                title=f"{normalized_ticker} market activity and operational update [ILLUSTRATIVE]",
                url=f"https://theedgemalaysia.com/market/{normalized_ticker.lower()}",
                domain="theedgemalaysia.com",
                published_date=now_iso,
                retrieved_at=now_iso,
                event_type="other",
                facts=[f"[ILLUSTRATIVE] Routine corporate operations for {normalized_ticker}."],
                stated_numbers=[],
                corroboration_count=1,
                unconfirmed=True,
                extraction_method="search_snippet",
            )
        ]

    async def get_news_for_ticker(
        self,
        ticker: str,
        query: str | None = None,
    ) -> list[NewsItem]:
        """Fetch news for ticker with caching, corroboration, and replay fallback."""
        normalized_ticker = ticker.upper().strip()
        cache_key = f"news:{normalized_ticker}:7"

        # 1. Replay mode: strictly pull from persistent stored news set, fallback to fixtures
        if self.mode == "replay":
            stored = await self.repo.get_stored_news_set(normalized_ticker)
            if stored and stored.items_json:
                return [NewsItem(**item) for item in stored.items_json]
            return self._get_fallback_fixtures(normalized_ticker)

        # 2. Check 30-minute short term cache
        cached = await self.repo.get_news_cache(cache_key, max_age_seconds=1800)
        if cached and cached.get("items"):
            cached_items = [NewsItem(**item) for item in cached["items"]]
            is_illustrative = any(
                "[ILLUSTRATIVE]" in item.title or any("[ILLUSTRATIVE]" in f for f in item.facts)
                for item in cached_items
            )
            if not (self.mode == "live" and self.tavily_gateway and self.tavily_gateway.enabled and is_illustrative):
                return cached_items

        # 3. Live mode with Tavily gateway available
        if self.mode == "live" and self.tavily_gateway and self.tavily_gateway.enabled:
            try:
                company_hint = TICKER_COMPANY_NAMES.get(normalized_ticker, normalized_ticker)
                search_query = query or f"{company_hint} ({normalized_ticker}) Malaysia stock financial news"
                raw_results = await self.tavily_gateway.search_news(search_query)

                # 7-day strict recency filter (FR-016)
                filtered = filter_7day_window(raw_results)

                # Sanitization and injection defense (FR-NEWS-09)
                sanitized = [sanitize_news_item(r) for r in filtered]

                # Convert to NewsItem and corroborate
                news_items = [NewsItem(**s) for s in sanitized if s.get("title") and s.get("url")]
                deduped = deduplicate_news(news_items)
                corroborated = corroborate_news(deduped, ticker=normalized_ticker)

                if corroborated:
                    # Cache in short-term cache and persist replay set
                    dumped = [item.model_dump() for item in corroborated]
                    await self.repo.set_news_cache(cache_key, {"items": dumped})
                    await self.repo.save_stored_news_set(
                        ticker=normalized_ticker,
                        items=dumped,
                        window_days=7,
                    )
                    return corroborated
            except Exception as err:
                # On live fetch error, log and gracefully fall back per Constitution IX
                logger.warning("tavily_news_fetch_failed", ticker=normalized_ticker, error=str(err))

        # 4. Sample / fallback mode: check stored news set or synthetic fixtures
        stored = await self.repo.get_stored_news_set(normalized_ticker)
        if stored and stored.items_json:
            result = [NewsItem(**item) for item in stored.items_json]
        else:
            result = self._get_fallback_fixtures(normalized_ticker)

        # Populate short-term cache
        dumped = [item.model_dump() for item in result]
        await self.repo.set_news_cache(cache_key, {"items": dumped})
        return result

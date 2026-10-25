"""Market data collector, scheduler, and quality guardian (T078, T120, FR-DATA-01 to 06, FR-007).

Coordinates:
- Tavily crawl primary collection when enabled with deterministic BeautifulSoup parsing.
- Direct screener fallback on crawl failure or budget exhaustion.
- SourceClient data fetching with pacing & kill-switch.
- Normalization and deduplication.
- Quality anomaly checks (suspect marking on >20% row drop).
- Persistence into SQLite append-only snapshots table with collector_source.
- Graceful failure keeping previous good snapshot active.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from warrantx.config import get_settings
from warrantx.data.normalize import normalize_snapshot_rows
from warrantx.data.quality import check_snapshot_quality
from warrantx.data.repo import AsyncRepository
from warrantx.data.source_client import SourceClient
from warrantx.data.tavily_crawler import TavilyWarrantCrawler

logger = logging.getLogger(__name__)

# Market open (09:15), midday (12:45), and market close (17:15)
SCHEDULE_POINTS_MYT = ["09:15", "11:30", "12:45", "14:45", "17:15"]


class Collector:
    """Orchestrates structured warrant market data collection cycles."""

    def __init__(
        self,
        repo: AsyncRepository,
        source_url: str | None = None,
        source_client: SourceClient | None = None,
        kill_switch: bool = False,
        crawler: TavilyWarrantCrawler | None = None,
        use_tavily_crawl: bool | None = None,
    ) -> None:
        self.repo = repo
        self.source_url = source_url
        self.kill_switch = kill_switch
        self.source_client = source_client or SourceClient(
            base_url=source_url, kill_switch=kill_switch
        )

        settings = get_settings()
        if use_tavily_crawl is None:
            self.use_tavily_crawl = getattr(settings, "tavily_crawl", False)
        else:
            self.use_tavily_crawl = use_tavily_crawl

        self.crawler = crawler or (
            TavilyWarrantCrawler(repo=repo) if self.use_tavily_crawl else None
        )

    def check_snapshot_quality(
        self, previous_count: int, current_rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Delegate quality check to quality engine."""
        return check_snapshot_quality(previous_count, current_rows)

    async def run_collection_cycle(self) -> dict[str, Any]:
        """Run a single collection, validation, and storage cycle."""
        if self.kill_switch:
            return {
                "status": "failed",
                "reason": "source_unavailable_or_kill_switch",
                "snapshot_id": None,
            }

        raw_rows: list[dict[str, Any]] = []
        collector_source = "direct_screener"

        # 1. Try Tavily crawl if enabled
        if self.use_tavily_crawl and self.crawler is not None:
            try:
                crawled_rows = await self.crawler.crawl_warrants()
                if crawled_rows:
                    raw_rows = crawled_rows
                    collector_source = "tavily_crawl"
                else:
                    logger.warning("Tavily crawl returned 0 rows, falling back to direct screener")
            except Exception as err:
                logger.warning("Tavily crawl failed (%s), falling back to direct screener", err)

        # 2. Direct screener fallback if crawl not active or returned no rows
        if not raw_rows:
            raw_payload = await self.source_client.fetch_raw_warrants()
            if raw_payload is None:
                return {
                    "status": "failed",
                    "reason": "source_unavailable_or_kill_switch",
                    "snapshot_id": None,
                }

            if isinstance(raw_payload, list):
                raw_rows = raw_payload
            elif isinstance(raw_payload, dict):
                if "data" in raw_payload and isinstance(raw_payload["data"], list):
                    raw_rows = raw_payload["data"]
                elif "rows" in raw_payload and isinstance(raw_payload["rows"], list):
                    raw_rows = raw_payload["rows"]
                elif "warrants" in raw_payload and isinstance(raw_payload["warrants"], list):
                    raw_rows = raw_payload["warrants"]

            collector_source = "direct_screener"

        if not raw_rows:
            return {
                "status": "failed",
                "reason": "empty_raw_payload",
                "snapshot_id": None,
            }

        # Normalize and deduplicate
        normalized_rows = normalize_snapshot_rows(raw_rows)
        if not normalized_rows:
            return {
                "status": "failed",
                "reason": "no_valid_rows_after_normalization",
                "snapshot_id": None,
            }

        # Compare quality against previous latest good snapshot
        prev_good = await self.repo.get_latest_good_snapshot()
        prev_count = prev_good.row_count if prev_good else 0

        quality = self.check_snapshot_quality(
            previous_count=prev_count,
            current_rows=normalized_rows,
        )

        is_suspect = quality.get("status") == "suspect"
        now_utc = datetime.now(timezone.utc)

        snapshot_meta = {
            "ok": True,
            "collector_source": collector_source,
            "fetched_at": now_utc.isoformat(),
            "source_last_update": now_utc.isoformat(),
            "note": "Scheduled collection cycle"
            if not is_suspect
            else "Quality warning: large row drop",
            "quality_json": quality,
        }

        saved_snap = await self.repo.save_snapshot(snapshot_meta, normalized_rows)

        # Upsert discovered underlyings
        for row in normalized_rows:
            ticker = row.get("underlying_ticker")
            if ticker:
                await self.repo.upsert_underlying(
                    ticker=ticker,
                    code=row.get("code", "")[:4],
                    name=ticker,
                )

        return {
            "status": "success",
            "snapshot_id": saved_snap.id,
            "collector_source": collector_source,
            "row_count": len(normalized_rows),
            "suspect": is_suspect,
            "quality": quality,
        }

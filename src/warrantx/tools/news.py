"""Search news analytical tool with 7-day recency window and Evidence envelope (T090, FR-NEWS-01..09).

Coordinates with NewsService to provide grounded, cited, corroborated news context
for underlying Bursa Malaysia equities.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from warrantx.data.repo import AsyncRepository
from warrantx.news.cache import NewsService
from warrantx.tools.evidence import Evidence
from warrantx.tools.models import NewsItem


class NewsSearchResult(BaseModel):
    """Result of news search for an underlying equity."""

    ticker: str
    news: list[NewsItem] = Field(default_factory=list)
    count: int = 0
    recency_window_days: int = 7
    evidence_id: str = ""
    mode: str = "sample"


async def search_news(
    ticker: str,
    query: str | None = None,
    service: NewsService | None = None,
    repo: AsyncRepository | None = None,
    mode: str = "sample",
    turn_id: str = "",
    evidence_index: int = 1,
) -> tuple[dict[str, Any], Evidence]:
    """Retrieve structured 7-day news items wrapped in an Evidence record."""
    clean_ticker = ticker.strip().upper()

    if service is None:
        if repo is None:
            from warrantx.data.repo import create_repo
            repo = create_repo(":memory:")
        service = NewsService(repo=repo, mode=mode, tavily_gateway=None)

    items = await service.get_news_for_ticker(clean_ticker, query=query)
    ev_id = f"E{evidence_index}"

    result = NewsSearchResult(
        ticker=clean_ticker,
        news=items,
        count=len(items),
        recency_window_days=7,
        evidence_id=ev_id,
        mode=service.mode,
    )

    result_dict = result.model_dump()

    source = "tavily" if service.mode == "live" else ("stored_replay" if service.mode == "replay" else "sample_fixtures")
    evidence = Evidence.wrap(
        evidence_id=ev_id,
        kind="news",
        source=source,
        payload=result_dict,
        summary=f"7-day verified news context for {clean_ticker} ({len(items)} items)",
        turn_id=turn_id or None,
    )

    if repo and turn_id:
        await repo.save_evidence(
            turn_id=turn_id,
            evidence_id=ev_id,
            kind="news",
            source=source,
            payload_json=result_dict,
        )

    return result_dict, evidence

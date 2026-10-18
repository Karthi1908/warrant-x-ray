"""Contract tests for GET /api/news and search_news tool (T090, FR-NEWS-01..09).

Tests:
1. GET /api/news returns 7-day news items with evidence envelope.
2. Query by ticker or query returns relevant items.
3. Every item contains mandatory provenance fields: url, domain, published_date, retrieved_at.
4. Items contain corroboration_count and unconfirmed flags.
5. Max results limit is respected.
"""

import pytest
from fastapi.testclient import TestClient

from warrantx.api.app import create_app
from warrantx.tools.news import search_news


@pytest.fixture
def test_client():
    import asyncio
    from warrantx.data.repo import create_repo
    repo = create_repo(":memory:")
    asyncio.run(repo.init_tables())
    app = create_app()
    app.state.repo = repo
    with TestClient(app) as client:
        yield client


def test_get_news_contract(test_client: TestClient):
    """GET /api/news returns 200 with schema matching FR-NEWS and evidence envelope."""
    resp = test_client.get("/api/news?ticker=MAYBANK")
    assert resp.status_code == 200
    data = resp.json()

    assert data["ticker"] == "MAYBANK"
    assert data["recency_window_days"] == 7
    assert "news" in data
    assert "count" in data
    assert "evidence" in data

    evidence = data["evidence"]
    assert evidence["kind"] == "news"
    assert "allowlist" in evidence
    assert len(evidence["allowlist"]) > 0

    news = data["news"]
    assert len(news) > 0
    item = news[0]
    assert "title" in item
    assert "url" in item
    assert "domain" in item
    assert "published_date" in item
    assert "retrieved_at" in item
    assert "corroboration_count" in item
    assert "unconfirmed" in item


def test_get_news_max_results_limit(test_client: TestClient):
    """GET /api/news respects max_results."""
    resp = test_client.get("/api/news?ticker=MAYBANK&max_results=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["news"]) <= 1


@pytest.mark.asyncio
async def test_search_news_tool():
    """search_news tool returns payload and Evidence with allowlist."""
    result, evidence = await search_news(ticker="TENAGA", evidence_index=3)

    assert result["ticker"] == "TENAGA"
    assert len(result["news"]) > 0
    assert evidence.id == "E3"
    assert evidence.kind == "news"
    assert "[E3]" in evidence.allowlist

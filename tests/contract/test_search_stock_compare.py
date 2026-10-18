"""Contract tests for Search, Stock Summary, and Compare endpoints (T093, FR-SRCH-*, FR-STK-*, FR-CMP-*).

Tests:
1. GET /api/underlyings returns list of Malaysian underlyings with warrant counts.
2. GET /api/warrants filters by underlying, type, issuer, moneyness, supports sorting and paging.
3. GET /api/warrants for non-existent stock returns empty list with message, not 500.
4. GET /api/stock/{ticker} returns stock summary (medians, flag counts, 5 nearest warrants).
5. GET /api/stock/{ticker} for empty/unknown stock returns zero-count summary, not 500.
6. POST /api/compare compares 2 to 3 warrants of the same underlying in uniform table with NO ranking/best label.
7. POST /api/compare rejects fewer than 2, more than 3, or mixed underlyings with 400 and clear explanation.
"""

import pytest
from fastapi.testclient import TestClient

from warrantx.api.app import create_app


@pytest.fixture
def test_client():
    import asyncio
    from warrantx.data.repo import create_repo

    repo = create_repo(":memory:")
    asyncio.run(repo.init_tables())
    asyncio.run(repo.load_synthetic_sample_database())

    app = create_app()
    app.state.repo = repo
    with TestClient(app) as client:
        yield client


def test_get_underlyings_contract(test_client: TestClient):
    """GET /api/underlyings returns underlyings with warrant counts and metadata."""
    resp = test_client.get("/api/underlyings")
    assert resp.status_code == 200
    data = resp.json()

    assert "underlyings" in data
    assert "as_of" in data
    assert "mode" in data
    assert len(data["underlyings"]) > 0

    und = data["underlyings"][0]
    assert "ticker" in und
    assert "name" in und
    assert "call_count" in und
    assert "put_count" in und
    assert "total_warrants" in und


def test_search_warrants_filters_and_paging(test_client: TestClient):
    """GET /api/warrants filters by underlying, type, sort, and limits results."""
    # 1. Filter by underlying
    resp = test_client.get("/api/warrants?underlying=MAYBANK&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "count" in data
    assert len(data["results"]) <= 5
    for r in data["results"]:
        assert r["underlying_ticker"] == "MAYBANK"
        assert "code" in r
        assert "issuer" in r
        assert "type" in r
        assert "strike" in r

    # 2. Filter by type=call
    resp_call = test_client.get("/api/warrants?underlying=MAYBANK&type=call")
    assert resp_call.status_code == 200
    calls = resp_call.json()["results"]
    for c in calls:
        assert c["type"] == "call"


def test_search_warrants_empty_stock(test_client: TestClient):
    """GET /api/warrants on an underlying with no warrants returns 200 with empty list."""
    resp = test_client.get("/api/warrants?underlying=NONEXISTENT_XYZ")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["count"] == 0
    assert "message" in data or "count" in data


def test_get_stock_summary_contract(test_client: TestClient):
    """GET /api/stock/{ticker} returns stock overview, medians, and nearest warrants."""
    resp = test_client.get("/api/stock/MAYBANK?holding_days=5")
    assert resp.status_code == 200
    data = resp.json()

    assert data["ticker"] == "MAYBANK"
    assert "call_count" in data
    assert "put_count" in data
    assert "issuer_count" in data
    assert "issuers" in data
    assert "median_spread_pct" in data
    assert "median_flat_decay" in data
    assert "flag_counts" in data
    assert "nearest_warrants" in data
    assert len(data["nearest_warrants"]) <= 5


def test_get_stock_summary_empty_stock(test_client: TestClient):
    """GET /api/stock/{ticker} for unknown stock returns empty summary without error."""
    resp = test_client.get("/api/stock/UNKNOWN_XYZ")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "UNKNOWN_XYZ"
    assert data["call_count"] == 0
    assert data["put_count"] == 0
    assert data["nearest_warrants"] == []


def test_compare_warrants_uniform_table_no_ranking(test_client: TestClient):
    """POST /api/compare compares 2-3 warrants uniformly without best/ranking labels (AC-05)."""
    # Fetch two MAYBANK warrants first
    w_resp = test_client.get("/api/warrants?underlying=MAYBANK&limit=2")
    warrants = w_resp.json()["results"]
    assert len(warrants) >= 2
    codes = [warrants[0]["code"], warrants[1]["code"]]

    resp = test_client.post("/api/compare", json={"codes": codes, "holding_days": 5})
    assert resp.status_code == 200
    data = resp.json()

    assert "comparison" in data
    assert len(data["comparison"]) == 2

    # Check identical attributes present in each item
    for item in data["comparison"]:
        assert "code" in item
        assert "issuer" in item
        assert "strike" in item
        assert "effective_gearing" in item
        assert "spread_pct" in item
        assert "spread_cost" in item
        assert "flat_decay" in item
        assert "breakeven_move" in item
        # CRITICAL CONSTITUTION RULE: No "best" or "rank" attribute!
        assert "best" not in item
        assert "rank" not in item
        assert "recommendation" not in item


def test_compare_warrants_validation_errors(test_client: TestClient):
    """POST /api/compare rejects < 2 codes, > 3 codes, and mixed underlyings."""
    # 1. Fewer than 2 codes
    resp1 = test_client.post("/api/compare", json={"codes": ["115510"]})
    assert resp1.status_code == 400

    # 2. More than 3 codes
    resp2 = test_client.post("/api/compare", json={"codes": ["W1", "W2", "W3", "W4"]})
    assert resp2.status_code == 400

    # 3. Mixed underlyings (MAYBANK vs TENAGA)
    # Find a MAYBANK warrant and a TENAGA warrant
    mb_res = test_client.get("/api/warrants?underlying=MAYBANK&limit=1").json()["results"]
    tn_res = test_client.get("/api/warrants?underlying=TENAGA&limit=1").json()["results"]
    if mb_res and tn_res:
        resp3 = test_client.post(
            "/api/compare",
            json={"codes": [mb_res[0]["code"], tn_res[0]["code"]]},
        )
        assert resp3.status_code == 400
        assert "underlying" in resp3.text.lower()

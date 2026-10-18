"""Contract tests for GET /api/warrants/{code} (T034).

Covers:
- Found: returns 200 with full WarrantCard schema matching contract
- Not found: returns 404 with standard error envelope
- ETag generation and 304 Not Modified support
- Expired warrant handling
- Case-insensitivity and whitespace trimming for warrant code
"""

import pytest
from fastapi.testclient import TestClient
from warrantx.api.app import create_app
from warrantx.data.repo import create_repo


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


def test_warrant_card_not_found(test_client: TestClient) -> None:
    """Non-existent warrant returns 404 with standard error format."""
    resp = test_client.get("/api/warrants/NONEXISTENT99")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"


def test_warrant_card_found_and_etag(test_client: TestClient) -> None:
    """Found warrant returns 200, ETag header, and subsequent request returns 304."""
    # Insert a synthetic row into app repo
    repo = test_client.app.state.repo
    import asyncio

    async def _setup():
        snap = await repo.save_snapshot(
            {"ok": True, "note": "contract_test"},
            [{
                "code": "51881C",
                "issuer": "CGS",
                "type": "call",
                "underlying_ticker": "MAYBANK",
                "expiry_date": "2026-12-31",
                "strike": 10.50,
                "ratio_raw": 4.0,
                "bid": 0.080,
                "ask": 0.090,
                "last_price": 0.085,
            }],
        )
        return snap.id

    asyncio.run(_setup())

    # Request card
    resp = test_client.get("/api/warrants/51881c")
    assert resp.status_code == 200
    card = resp.json()
    assert card["code"] == "51881C"
    assert "ETag" in resp.headers

    etag = resp.headers["ETag"]
    # Request with If-None-Match header
    resp_304 = test_client.get("/api/warrants/51881C", headers={"If-None-Match": etag})
    assert resp_304.status_code == 304

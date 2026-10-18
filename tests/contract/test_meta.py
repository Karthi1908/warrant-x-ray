"""Contract tests for GET /api/meta and GET /api/snapshots (T074, FR-DATA-08, FR-ERR-21).

Tests:
1. GET /api/meta returns mode, as_of, market status, staleness, and public usage metrics.
2. GET /api/snapshots lists available snapshots.
3. snapshot_id pinning returns data for the specific pinned snapshot.
4. Non-existent snapshot_id returns 404 with standard error envelope.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from warrantx.api.app import create_app


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


@pytest.fixture
def seeded_snapshots(test_client: TestClient):
    repo = test_client.app.state.repo

    async def _setup():
        snap1 = await repo.save_snapshot(
            {"ok": True, "note": "snapshot_1", "fetched_at": "2026-10-14T09:30:00Z"},
            [{"code": "115510", "issuer": "CGS", "type": "call", "underlying_ticker": "MAYBANK", "expiry_date": "2027-06-30", "strike": 10.5, "ratio_raw": 4.0}],
        )
        snap2 = await repo.save_snapshot(
            {"ok": True, "note": "snapshot_2", "fetched_at": "2026-10-14T11:30:00Z"},
            [{"code": "115510", "issuer": "CGS", "type": "call", "underlying_ticker": "MAYBANK", "expiry_date": "2027-06-30", "strike": 10.5, "ratio_raw": 4.0, "bid": 0.160, "ask": 0.170}],
        )
        # Record some usage metrics
        await repo.record_visit("session_test_1")
        await repo.record_daily_unique("192.168.1.0/24", "Mozilla/5.0")
        await repo.record_interactive_query("2026-10-14")
        return snap1.id, snap2.id

    return asyncio.run(_setup())


def test_get_meta_contract(test_client: TestClient, seeded_snapshots):
    """GET /api/meta matches standard schema with public usage metrics."""
    resp = test_client.get("/api/meta")
    assert resp.status_code == 200
    data = resp.json()

    assert "mode" in data
    assert "as_of" in data
    assert "market_open" in data
    assert "stale" in data
    assert "usage_metrics" in data

    metrics = data["usage_metrics"]
    assert "total_visits" in metrics
    assert "daily_uniques" in metrics
    assert "interactive_queries" in metrics


def test_get_snapshots_contract(test_client: TestClient, seeded_snapshots):
    """GET /api/snapshots returns array of stored snapshots."""
    resp = test_client.get("/api/snapshots")
    assert resp.status_code == 200
    data = resp.json()

    assert "snapshots" in data
    assert len(data["snapshots"]) >= 2
    first = data["snapshots"][0]
    assert "id" in first
    assert "fetched_at" in first


def test_snapshot_id_pinning(test_client: TestClient, seeded_snapshots):
    """Pinning snapshot_id returns data as-of that specific snapshot."""
    snap1_id, snap2_id = seeded_snapshots

    resp1 = test_client.get(f"/api/warrants/115510?snapshot_id={snap1_id}")
    assert resp1.status_code == 200

    resp2 = test_client.get(f"/api/warrants/115510?snapshot_id={snap2_id}")
    assert resp2.status_code == 200
    assert resp2.json()["bid"] == 0.160


def test_nonexistent_snapshot_id_returns_404(test_client: TestClient):
    """Querying a non-existent snapshot_id returns 404."""
    resp = test_client.get("/api/warrants/115510?snapshot_id=999999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"

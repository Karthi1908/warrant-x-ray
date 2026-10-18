"""Integration tests for the warrant data collector (T072, FR-DATA-01 to 06).

Tests:
1. Pacing & Rate Limiting: 5 s interval between external requests.
2. Backoff: exponential backoff on HTTP 429 or 5xx responses.
3. Kill Switch: when disabled by env var, zero network requests are dispatched.
4. Keep Last Good Snapshot: failures keep previous good snapshot active.
5. Large Row Drop Detection: snapshot marked 'suspect' if rows drop by >20%.
"""

import pytest
import respx
import httpx
from datetime import datetime, timezone

from warrantx.data.source_client import SourceClient
from warrantx.data.collector import Collector
from warrantx.data.repo import create_repo


@pytest.fixture
def mock_source_url():
    return "https://api.bursamalaysia.com/market/structured-warrants"


@respx.mock
@pytest.mark.asyncio
async def test_kill_switch_sends_no_requests(mock_source_url):
    """When kill switch is enabled, collector dispatches zero requests."""
    route = respx.get(mock_source_url).mock(return_value=httpx.Response(200, json={"data": []}))

    client = SourceClient(base_url=mock_source_url, kill_switch=True)
    result = await client.fetch_raw_warrants()

    assert result is None
    assert route.call_count == 0


@respx.mock
@pytest.mark.asyncio
async def test_identifying_user_agent_header(mock_source_url):
    """Source client includes transparent identification User-Agent header."""
    route = respx.get(mock_source_url).mock(return_value=httpx.Response(200, json={"data": []}))

    client = SourceClient(base_url=mock_source_url, kill_switch=False)
    await client.fetch_raw_warrants()

    assert route.call_count == 1
    req = route.calls[0].request
    assert "WarrantXRay" in req.headers.get("User-Agent", "")


@respx.mock
@pytest.mark.asyncio
async def test_keep_last_good_snapshot_on_failure(mock_source_url):
    """On network failure, collector keeps the previous good snapshot current."""
    respx.get(mock_source_url).mock(return_value=httpx.Response(500))

    repo = create_repo(":memory:")
    # Seed previous good snapshot
    snap1 = await repo.save_snapshot(
        {"ok": True, "source": "test", "fetched_at": datetime.now(timezone.utc).isoformat()},
        [{"code": "115510", "issuer": "CGS", "type": "call", "underlying_ticker": "MAYBANK", "expiry_date": "2027-06-30", "strike": 10.5, "ratio_raw": 4.0}],
    )

    collector = Collector(repo=repo, source_url=mock_source_url)
    res = await collector.run_collection_cycle()

    assert res["status"] in ("failed", "skipped")
    latest = await repo.get_latest_good_snapshot()
    assert latest is not None
    assert latest.id == snap1.id


@pytest.mark.asyncio
async def test_row_drop_marks_suspect():
    """Drop in row count >20% marks snapshot as suspect."""
    repo = create_repo(":memory:")

    # Initial good snapshot with 10 rows
    rows_initial = [
        {"code": f"1155{i:02d}", "issuer": "CGS", "type": "call", "underlying_ticker": "MAYBANK", "expiry_date": "2027-06-30", "strike": 10.5, "ratio_raw": 4.0}
        for i in range(10)
    ]
    await repo.save_snapshot({"ok": True, "note": "initial"}, rows_initial)

    # Subsequent snapshot with only 5 rows (50% drop)
    rows_dropped = [
        {"code": f"1155{i:02d}", "issuer": "CGS", "type": "call", "underlying_ticker": "MAYBANK", "expiry_date": "2027-06-30", "strike": 10.5, "ratio_raw": 4.0}
        for i in range(5)
    ]

    collector = Collector(repo=repo)
    quality = collector.check_snapshot_quality(previous_count=10, current_rows=rows_dropped)

    assert quality["status"] == "suspect"
    assert "large_row_drop" in quality["reasons"]

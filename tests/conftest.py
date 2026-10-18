"""Shared pytest fixtures for Warrant X-Ray test suite."""

import json
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from warrantx.data.repo import AsyncRepository, Base


@pytest.fixture
def synthetic_fixtures() -> dict:
    """Load the synthetic market snapshot fixture."""
    path = Path("tests/fixtures/synthetic_snapshot.json")
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@pytest_asyncio.fixture
async def test_repo():
    """Create an isolated in-memory SQLite async repository."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    repo = AsyncRepository(engine)
    repo.db_url = "sqlite+aiosqlite:///:memory:"

    # Seed initial test snapshot with MAYBANK warrant 115510
    await repo.save_snapshot(
        snapshot_data={"ok": True, "note": "test_seed"},
        rows_data=[
            {
                "code": "115510",
                "issuer": "CGS",
                "type": "call",
                "underlying_ticker": "MAYBANK",
                "expiry_date": "2027-06-30",
                "strike": 10.50,
                "ratio_raw": 4.0,
                "underlying_bid": 10.20,
                "bid": 0.150,
                "ask": 0.155,
                "last_price": 0.152,
                "issuer_iv": 42.0,
                "issuer_eg": 5.2,
                "issuer_delta": 0.52,
            },
            {
                "code": "51881C",
                "issuer": "CGS",
                "type": "call",
                "underlying_ticker": "MAYBANK",
                "expiry_date": "2026-12-31",
                "strike": 10.50,
                "ratio_raw": 4.0,
                "underlying_bid": 10.20,
                "bid": 0.080,
                "ask": 0.090,
                "last_price": 0.085,
            },
        ],
    )

    yield repo
    await engine.dispose()

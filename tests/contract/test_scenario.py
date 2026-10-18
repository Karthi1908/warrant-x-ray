"""Contract and parity tests for POST /api/scenario and scenario tool (T066).

AC-03: Scenario results from the REST API endpoint and the agent tool must be 100% identical.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from warrantx.api.app import create_app
from warrantx.tools.scenario import run_scenario_tool


@pytest.fixture
def test_client():
    from warrantx.data.repo import create_repo
    repo = create_repo(":memory:")
    asyncio.run(repo.init_tables())
    app = create_app()
    app.state.repo = repo
    with TestClient(app) as client:
        yield client


@pytest.fixture
def seeded_warrant(test_client: TestClient):
    repo = test_client.app.state.repo

    async def _setup():
        snap = await repo.save_snapshot(
            {"ok": True, "note": "scenario_contract_test"},
            [
                {
                    "code": "115510",
                    "issuer": "CGS",
                    "type": "call",
                    "underlying_ticker": "MAYBANK",
                    "expiry_date": "2027-06-30",
                    "strike": 10.50,
                    "ratio_raw": 4.0,
                    "underlying_price": 10.20,
                    "bid": 0.150,
                    "ask": 0.160,
                    "last_price": 0.155,
                }
            ],
        )
        return snap.id

    asyncio.run(_setup())
    return "115510"


def test_scenario_contract_parity(test_client: TestClient, seeded_warrant: str):
    """POST /api/scenario matches tool execution exactly (AC-03)."""
    payload = {
        "code": seeded_warrant,
        "move": 0.05,
        "days": 3,
        "iv_shift": -5.0,
    }

    # API call
    resp = test_client.post("/api/scenario", json=payload)
    assert resp.status_code == 200
    api_result = resp.json()

    # Tool call
    tool_result = run_scenario_tool(
        repo=test_client.app.state.repo,
        code=seeded_warrant,
        move=0.05,
        days=3,
        iv_shift=-5.0,
    )

    # Parity check
    assert api_result["entry_price"] == tool_result.entry_price
    assert api_result["exit_price"] == tool_result.exit_price
    assert api_result["pnl_pct"] == tool_result.pnl_pct
    assert api_result["breakeven_move"] == tool_result.breakeven_move
    assert len(api_result["curve"]) == len(tool_result.curve)


def test_scenario_contract_range_rejection(test_client: TestClient, seeded_warrant: str):
    """Out-of-range inputs return 422 with error message naming the valid range."""
    # Out of range move > 0.5
    resp = test_client.post(
        "/api/scenario",
        json={"code": seeded_warrant, "move": 0.75, "days": 0, "iv_shift": 0.0},
    )
    assert resp.status_code in (400, 422)
    assert "[-0.5, 0.5]" in resp.text or "less than or equal to 0.5" in resp.text

    # Negative days
    resp_days = test_client.post(
        "/api/scenario",
        json={"code": seeded_warrant, "move": 0.0, "days": -5, "iv_shift": 0.0},
    )
    assert resp_days.status_code in (400, 422)


def test_scenario_not_found(test_client: TestClient):
    """Non-existent warrant returns 404."""
    resp = test_client.post(
        "/api/scenario",
        json={"code": "UNKNOWN99", "move": 0.0, "days": 0, "iv_shift": 0.0},
    )
    assert resp.status_code == 404

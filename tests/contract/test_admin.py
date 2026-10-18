"""Contract tests for admin endpoints (T101, FR-020, FR-023, FR-CTRL-02).

Tests:
1. When WX_ADMIN_TOKEN is unset, /api/admin routes return 404 (router not mounted).
2. When WX_ADMIN_TOKEN is set:
   - Missing or invalid Bearer token returns 401 Unauthorized.
   - Valid Bearer token allows GET /api/admin/metrics returning complete operator data.
   - Valid Bearer token allows POST /api/admin/cache/clear.
   - Valid Bearer token allows POST /api/admin/budget/reset.
"""

from __future__ import annotations

import asyncio
import pytest
from fastapi.testclient import TestClient

from warrantx.api.app import create_app
from warrantx.config import Settings
from warrantx.llm.usage import get_malaysia_today


def test_admin_routes_unmounted_when_token_unset():
    """Admin routes are not mounted when admin_token is empty or unset."""
    settings = Settings(admin_token="")
    app = create_app(settings=settings)
    with TestClient(app) as client:
        resp = client.get("/api/admin/metrics")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


def test_admin_routes_auth_required():
    """Admin endpoints reject requests without a valid Bearer token."""
    settings = Settings(admin_token="super_secret_admin_token")
    app = create_app(settings=settings)
    with TestClient(app) as client:
        # 1. Missing Authorization header
        resp = client.get("/api/admin/metrics")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthorized"

        # 2. Invalid Authorization header format
        resp = client.get(
            "/api/admin/metrics",
            headers={"Authorization": "Basic super_secret_admin_token"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthorized"

        # 3. Wrong token value
        resp = client.get(
            "/api/admin/metrics",
            headers={"Authorization": "Bearer wrong_token_value"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthorized"


def test_get_admin_metrics_authorized():
    """GET /api/admin/metrics returns comprehensive operational metrics (FR-020, FR-023)."""
    settings = Settings(admin_token="super_secret_admin_token")
    app = create_app(settings=settings)
    with TestClient(app) as client:
        repo = app.state.repo

        # Seed some test LLM calls and usage metrics
        async def _seed():
            today = get_malaysia_today()
            await repo.log_llm_call(
                model="meta/llama-3.3-70b-instruct",
                tier="ultra",
                purpose="chat_reasoning",
                in_tokens=500,
                out_tokens=150,
                latency_ms=1200,
                cost_usd=0.00045,
            )
            await repo.record_visit(today, is_new_unique=True)
            await repo.record_interactive_query(today)

        asyncio.run(_seed())

        resp = client.get(
            "/api/admin/metrics",
            headers={"Authorization": "Bearer super_secret_admin_token"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "ok"

        # Verify budget details
        budget = data["budget"]
        assert "used_usd" in budget
        assert "limit_usd" in budget
        assert "remaining_usd" in budget
        assert "is_exhausted" in budget

        # Verify LLM cost data
        llm_costs = data["llm_costs"]
        assert llm_costs["total_calls"] >= 1
        assert "by_tier" in llm_costs
        assert "by_day" in llm_costs
        assert "by_purpose" in llm_costs

        # Verify usage metrics
        usage = data["usage_metrics"]
        assert len(usage) >= 1
        first_usage = usage[0]
        assert "visits" in first_usage
        assert "unique_visitors" in first_usage
        assert "interactive_queries" in first_usage

        # Verify operator config (FR-023)
        cfg = data["config"]
        assert cfg["risk_free_rate"] == 0.03
        assert "flags" in cfg
        assert "model_ultra" in cfg


def test_admin_cache_clear_authorized():
    """POST /api/admin/cache/clear clears temporary cached data."""
    settings = Settings(admin_token="super_secret_admin_token")
    app = create_app(settings=settings)
    with TestClient(app) as client:
        repo = app.state.repo

        async def _seed_cache():
            await repo.set_news_cache("news:MAYBANK", {"articles": []})

        asyncio.run(_seed_cache())

        resp = client.post(
            "/api/admin/cache/clear",
            headers={"Authorization": "Bearer super_secret_admin_token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cleared"
        assert data["deleted_entries"] >= 1


def test_admin_budget_reset_authorized():
    """POST /api/admin/budget/reset resets daily LLM spend."""
    settings = Settings(admin_token="super_secret_admin_token")
    app = create_app(settings=settings)
    with TestClient(app) as client:
        repo = app.state.repo

        async def _seed_spend():
            today = get_malaysia_today()
            await repo.increment_budget(day=today, kind="llm_usd", amount=5.50)

        asyncio.run(_seed_spend())

        resp = client.post(
            "/api/admin/budget/reset",
            headers={"Authorization": "Bearer super_secret_admin_token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "reset"
        assert data["budget"]["used_usd"] == 0.0

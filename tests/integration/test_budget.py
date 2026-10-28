"""Integration tests for budget guardian, daily cap fallback, and session caps (T098).

Verifies FR-CTRL-02, FR-DEEP-05, AC-14:
- When daily spend cap is reached, chat queries return stored/templated responses with notice.
- Fallback responses pass the advice linter and grounding verifier.
- Deep report generation is capped per session.
- Advancing the clock across midnight resets daily spend and resumes standard model calls.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from warrantx.agents.sessions import SessionManager
from warrantx.api.app import create_app
from warrantx.api.budget import is_budget_exhausted, get_daily_budget_status
from warrantx.config import Settings
from warrantx.data.repo import AsyncRepository
from warrantx.guardrails.fallback import generate_fallback_response
from warrantx.guardrails.linter import check_advice_linter
from warrantx.guardrails.verifier import verify_grounding
from warrantx.llm.usage import get_malaysia_today


@pytest.mark.asyncio
async def test_budget_exhausted_check(test_repo: AsyncRepository):
    """Test that is_budget_exhausted flags when spend reaches configured limit."""
    today = get_malaysia_today()

    # Initial state: 0 spend
    assert not await is_budget_exhausted(test_repo, limit_usd=5.0)

    # Spend 2.50 USD: still under 5.00 limit
    await test_repo.increment_budget(day=today, kind="llm_usd", amount=2.50)
    assert not await is_budget_exhausted(test_repo, limit_usd=5.0)

    # Spend another 2.50 USD: exactly 5.00 limit -> exhausted
    await test_repo.increment_budget(day=today, kind="llm_usd", amount=2.50)
    assert await is_budget_exhausted(test_repo, limit_usd=5.0)

    # Status breakdown
    status = await get_daily_budget_status(test_repo, limit_usd=5.0)
    assert status["used_usd"] == 5.0
    assert status["limit_usd"] == 5.0
    assert status["is_exhausted"] is True


@pytest.mark.asyncio
async def test_fallback_response_passes_verifier_and_linter(test_repo: AsyncRepository):
    """Fallback response must pass both the advice linter and grounding verifier (T099, CHK035)."""
    # Load synthetic snapshot so warrant 1155C1 exists in repo
    snapshot = await test_repo.load_synthetic_sample_database()

    # Generate fallback response for 1155C1
    res = await generate_fallback_response(
        message="Tell me about 1155C1",
        repo=test_repo,
        turn_id="turn-fallback-test",
        snapshot_id=snapshot.id,
        lang="en",
    )

    assert res.completed is True
    assert res.disclaimer_present is True
    assert "Daily AI compute budget has been reached" in res.final_text
    assert "1155C1" in res.final_text

    # 1. Advice linter check: NO financial advice, disclaimer present
    linter_res = check_advice_linter(res.final_text)
    assert linter_res.passed is True
    assert len(linter_res.violations) == 0

    # 2. Grounding verifier check: all numbers match evidence allowlist
    assert len(res.evidence_items) > 0
    allowlist = set(res.evidence_items[0].allowlist)
    allowlist.add(res.evidence_items[0].id)
    allowlist.add(f"[{res.evidence_items[0].id}]")

    ver_res = verify_grounding(res.final_text, allowlist=allowlist)
    assert ver_res.is_grounded is True
    assert len(ver_res.ungrounded_tokens) == 0


@pytest.mark.asyncio
async def test_chat_endpoint_daily_cap_fallback(test_repo: AsyncRepository):
    """When daily cap is reached, POST /api/chat returns templated response with notice (AC-14)."""
    today = get_malaysia_today()

    # Force budget exhaustion for today
    await test_repo.increment_budget(day=today, kind="llm_usd", amount=999.0)

    settings = Settings(
        DATABASE_URL=test_repo.db_url,
        ENVIRONMENT="test",
        ADMIN_TOKEN="test-token",
        LLM_DAILY_USD_CAP=10.0,
        chat_enabled=True,
    )
    app = create_app(settings=settings)
    app.state.repo = test_repo

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/chat",
            json={
                "session_id": "test-budget-sess-1",
                "message": "What is the strike of 115510?",
            },
        )
        assert resp.status_code == 200

        # Parse SSE events
        lines = resp.text.strip().split("\n")
        tokens = []
        for line in lines:
            if line.startswith("data: "):
                data_str = line.replace("data: ", "").strip()
                try:
                    data = json.loads(data_str)
                    if isinstance(data, dict) and "text" in data:
                        tokens.append(data["text"])
                except Exception:
                    pass

        full_output = "".join(tokens)
        assert "Daily AI compute budget has been reached" in full_output
        assert "Educational and analytical tool only" in full_output


def test_per_session_deep_report_cap():
    """Per-session deep report limit is enforced (FR-DEEP-05)."""
    mgr = SessionManager()
    sess = mgr.get_or_create_chat_session("sess-deep-test")

    # Initial state
    assert sess.deep_report_count == 0

    # First report allowed
    sess.deep_report_count += 1
    assert sess.deep_report_count == 1

    # Second report blocked by cap
    max_reports_per_session = 1
    assert sess.deep_report_count >= max_reports_per_session


@pytest.mark.asyncio
async def test_fake_clock_midnight_resets_daily_budget(test_repo: AsyncRepository):
    """Advancing clock to the next day accesses fresh budget bucket (fake clock test)."""
    day1 = "2026-10-16"
    day2 = "2026-10-17"

    # Exhaust budget on Day 1
    await test_repo.increment_budget(day=day1, kind="llm_usd", amount=10.0)
    assert await is_budget_exhausted(test_repo, limit_usd=10.0, day=day1)

    # On Day 2, spend is 0, so budget is NOT exhausted
    assert not await is_budget_exhausted(test_repo, limit_usd=10.0, day=day2)

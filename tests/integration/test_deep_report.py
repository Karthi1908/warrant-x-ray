"""Integration tests for Deep Risk Report workflow with SequentialAgent (T104, FR-DEEP-01 to 06, AC-17).

Tests:
1. Four-step pipeline (collect, draft, red-team review, assemble) produces all 6 sections + disclaimer.
2. Red-team adversarial findings appear under `counterpoints`.
3. Output passes advice linter and grounding checks with 0 violations.
4. Report caching and reuse for (code, snapshot_id, holding_days).
5. Per-session deep report cap (3 reports per session).
6. Fallback to standard structured answer on failure.
"""

from __future__ import annotations

import pytest

from warrantx.agents.deep_report import SequentialAgent, reset_deep_report_session_counts
from warrantx.data.repo import create_repo
from warrantx.guardrails.linter import check_advice_linter
from warrantx.llm.fake import FakeLlm


@pytest.fixture
def repo_with_snapshot():
    repo = create_repo("sqlite+aiosqlite:///:memory:")

    async def _setup():
        await repo.init_tables()
        snap = await repo.save_snapshot(
            {"ok": True, "note": "deep_report_test", "fetched_at": "2026-10-15T09:30:00Z"},
            [
                {
                    "code": "115510",
                    "issuer": "CGS",
                    "type": "call",
                    "underlying_ticker": "MAYBANK",
                    "expiry_date": "2027-06-30",
                    "strike": 10.5,
                    "ratio_raw": 4.0,
                    "bid": 0.160,
                    "ask": 0.170,
                    "underlying_bid": 10.20,
                    "underlying_ask": 10.22,
                }
            ],
        )
        return repo, snap.id

    import asyncio
    return asyncio.run(_setup())


@pytest.mark.asyncio
async def test_deep_report_workflow_and_sections(repo_with_snapshot):
    """FR-DEEP-01, FR-DEEP-02, FR-DEEP-03: SequentialAgent generates all sections with red-team counterpoints."""
    repo, snap_id = repo_with_snapshot
    fake_llm = FakeLlm()
    agent = SequentialAgent(llm=fake_llm, repo=repo)

    result = await agent.generate_report(
        code="115510",
        holding_days=5,
        snapshot_id=snap_id,
        session_id="session_test_deep_1",
    )

    assert result["ok"] is True
    report = result["report"]

    # FR-DEEP-01: Verify all 6 required sections + disclaimer
    assert "summary" in report
    assert "cost_breakdown" in report
    assert "what_must_go_right" in report
    assert "key_risks" in report
    assert "counterpoints" in report
    assert "data_limits" in report
    assert "disclaimer" in report

    # FR-DEEP-02: Counterpoints populated with adversarial review findings
    assert len(report["counterpoints"]) >= 1
    counterpoints_text = " ".join(report["counterpoints"])
    assert any(term in counterpoints_text.lower() for term in ["risk", "spread", "decay", "issuer", "trap", "hurdle"])

    # FR-DEEP-03: Advice linter check on all generated textual content
    all_text = f"{report['summary']} {counterpoints_text} {' '.join(report['what_must_go_right'])} {report['disclaimer']}"
    linter_res = check_advice_linter(all_text)
    assert linter_res.passed is True
    assert len(linter_res.violations) == 0

    # Verify pipeline status history
    assert len(result["status_history"]) >= 4
    assert any("collect" in s.lower() for s in result["status_history"])
    assert any("draft" in s.lower() for s in result["status_history"])
    assert any("red-team" in s.lower() or "review" in s.lower() for s in result["status_history"])
    assert any("assemble" in s.lower() for s in result["status_history"])


@pytest.mark.asyncio
async def test_deep_report_caching_and_reuse(repo_with_snapshot):
    """FR-DEEP-05: Subsequent requests with same (code, snapshot_id, holding_days) reuse cached report."""
    repo, snap_id = repo_with_snapshot
    fake_llm = FakeLlm()
    agent = SequentialAgent(llm=fake_llm, repo=repo)

    # 1. First run generates and caches
    res1 = await agent.generate_report(
        code="115510",
        holding_days=5,
        snapshot_id=snap_id,
        session_id="session_reuse_test",
    )
    assert res1["ok"] is True
    assert res1.get("cached") is False

    # 2. Second run for same key returns cached copy
    res2 = await agent.generate_report(
        code="115510",
        holding_days=5,
        snapshot_id=snap_id,
        session_id="session_reuse_test",
    )
    assert res2["ok"] is True
    assert res2.get("cached") is True
    assert res2["report"]["code"] == res1["report"]["code"]


@pytest.mark.asyncio
async def test_deep_report_per_session_cap(repo_with_snapshot):
    """FR-DEEP-05: Enforce cap of 3 reports per browser session."""
    repo, snap_id = repo_with_snapshot
    fake_llm = FakeLlm()
    agent = SequentialAgent(llm=fake_llm, repo=repo)
    session_id = "session_cap_enforcement_test"
    reset_deep_report_session_counts()

    # Generate 3 reports across different holding days so cache is not hit
    for d in [1, 3, 5]:
        res = await agent.generate_report(
            code="115510",
            holding_days=d,
            snapshot_id=snap_id,
            session_id=session_id,
        )
        assert res["ok"] is True

    # 4th uncached report must be rejected under session limit
    res4 = await agent.generate_report(
        code="115510",
        holding_days=10,
        snapshot_id=snap_id,
        session_id=session_id,
    )
    assert res4["ok"] is False
    assert res4["error"] == "rate_limited"
    assert "limit (3) reached" in res4["message"].lower()


@pytest.mark.asyncio
async def test_deep_report_fallback_on_failure(repo_with_snapshot):
    """FR-DEEP-06: On agent failure or model error, falls back to standard answer with notice."""
    repo, snap_id = repo_with_snapshot

    class BrokenLlm(FakeLlm):
        async def generate(self, *args, **kwargs):
            raise RuntimeError("Model service unavailable")

    agent = SequentialAgent(llm=BrokenLlm(), repo=repo)

    result = await agent.generate_report(
        code="115510",
        holding_days=5,
        snapshot_id=snap_id,
        session_id="session_fallback_test",
    )

    assert result["ok"] is True
    assert result.get("fallback") is True
    report = result["report"]
    assert "summary" in report
    assert "cost_breakdown" in report
    assert "disclaimer" in report

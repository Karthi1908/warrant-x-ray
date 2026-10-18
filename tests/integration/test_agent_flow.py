"""Integration tests for agent flow, tool calling, grounding, and guardrails.

Implements T047 (FR-CHAT-*, FR-ERR-16, FR-ERR-17).
"""

import pytest

from warrantx.agents.root import RootAgent
from warrantx.llm.fake import FakeLlm
from warrantx.tools.evidence import Evidence


@pytest.mark.asyncio
async def test_agent_flow_factual_turn_with_tool_call(test_repo, synthetic_fixtures):
    """Verify end-to-end agent turn with tool execution, evidence capture, and verified response."""
    fake_llm = FakeLlm(
        scripted_calls=[
            {
                "tool_calls": [
                    {
                        "name": "get_warrant_card",
                        "args": {"code": "115510", "holding_days": 5},
                    }
                ],
                "content": "",
            },
            {
                "tool_calls": [],
                "content": (
                    "Warrant 115510 has a bid of RM 0.150 and ask of RM 0.155 [E1]. "
                    "The implied volatility is 19.0% with effective gearing 8.56x."
                ),
            },
        ]
    )

    agent = RootAgent(llm=fake_llm, repo=test_repo)
    turn = await agent.run_turn(
        message="What are the quotes and gearing for 115510?",
        session_id="test-session-1",
    )

    assert turn.completed is True
    assert len(turn.evidence_items) > 0
    assert turn.evidence_items[0].kind == "card"
    assert "RM 0.150" in turn.final_text
    assert turn.disclaimer_present is True
    assert turn.advice_refused is False


@pytest.mark.asyncio
async def test_agent_flow_advice_refusal_without_model_call(test_repo):
    """Verify that financial advice queries are refused immediately at pre-check."""
    fake_llm = FakeLlm(scripted_calls=[])  # Should not be called
    agent = RootAgent(llm=fake_llm, repo=test_repo)

    turn = await agent.run_turn(
        message="Should I buy this warrant right now for maximum return?",
        session_id="test-session-2",
    )

    assert turn.completed is True
    assert turn.advice_refused is True
    assert len(fake_llm.history) == 0
    assert "cannot provide investment advice" in turn.final_text.lower()


@pytest.mark.asyncio
async def test_agent_flow_strip_and_note_on_unverified_figure(test_repo):
    """Verify that ungrounded numbers undergo 1 regeneration attempt then strip-and-note."""
    fake_llm = FakeLlm(
        scripted_calls=[
            {
                "tool_calls": [
                    {
                        "name": "get_warrant_card",
                        "args": {"code": "115510", "holding_days": 5},
                    }
                ],
                "content": "",
            },
            # First draft with hallucinated 999.0%
            {
                "tool_calls": [],
                "content": "Warrant 115510 has a bid of RM 0.150 [E1]. The expected return is 999.0%.",
            },
            # Second draft retry still contains 999.0%
            {
                "tool_calls": [],
                "content": "Warrant 115510 has a bid of RM 0.150 [E1]. The expected return is 999.0%.",
            },
        ]
    )

    agent = RootAgent(llm=fake_llm, repo=test_repo)
    turn = await agent.run_turn(
        message="What is the expected return for 115510?",
        session_id="test-session-3",
    )

    assert turn.completed is True
    assert "999.0%" not in turn.final_text
    assert "omitted" in turn.final_text.lower()

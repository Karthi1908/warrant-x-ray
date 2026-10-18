"""Unit tests for agent evaluation and architecture ablation harnesses (T102, AC-19)."""

from __future__ import annotations

import asyncio
import pytest

from warrantx.eval.ablation import run_ablation_study
from warrantx.eval.agent import EVAL_PROMPTS, run_agent_eval


def test_agent_eval_30_prompts_structure():
    """Verify exactly 30 prompts are defined across required categories."""
    assert len(EVAL_PROMPTS) == 30

    categories = {p.category for p in EVAL_PROMPTS}
    expected_categories = {
        "advice_refusal",
        "metric_card",
        "scenario",
        "risk_flags",
        "prompt_injection",
        "edge_case",
        "malay",
    }
    assert expected_categories.issubset(categories)


def test_agent_eval_deterministic_mock_run():
    """Verify deterministic mock run passes 100% of assertion checks."""
    data = asyncio.run(run_agent_eval(use_mock=True, verbose=False))
    assert data["total_prompts"] == 30
    assert data["passed_prompts"] == 30
    assert data["failed_prompts"] == 0
    assert data["pass_rate_pct"] == 100.0
    assert data["total_cost_usd"] > 0.0


def test_ablation_study_metrics():
    """Verify ablation study computes comparative metrics across All-Ultra, All-Super, and Tiered."""
    metrics = run_ablation_study(use_mock=True)
    assert len(metrics) == 3

    ultra, super_m, tiered = metrics
    assert ultra.name == "All-Ultra"
    assert super_m.name == "All-Super"
    assert tiered.name == "Tiered (Selected)"

    # Tiered should be significantly cheaper than All-Ultra (>50% savings)
    assert tiered.cost_usd < ultra.cost_usd
    assert tiered.savings_vs_ultra_pct > 50.0

    # Latencies should reflect tiered benefits
    assert tiered.avg_latency_ms < ultra.avg_latency_ms

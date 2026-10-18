"""Unit tests for scripts/cost_report.py (T100, AC-19)."""

from __future__ import annotations

import asyncio
import io
import sys
from unittest.mock import patch
import pytest

from scripts.cost_report import format_markdown_table, generate_report
from warrantx.data.repo import create_repo


def test_format_markdown_table():
    """Verify markdown table formatting."""
    headers = ["Tier", "Calls", "Cost USD"]
    rows = [
        ["ultra", "10", "$0.005000"],
        ["super", "25", "$0.003500"],
    ]
    table = format_markdown_table(headers, rows)
    assert "| Tier" in table
    assert "| Calls" in table
    assert "| Cost USD" in table
    assert "| ultra" in table
    assert "| super" in table
    assert "---" in table


@pytest.mark.asyncio
async def test_generate_report_output():
    """Verify generate_report executes without error against a repo with logged calls."""
    repo = create_repo("sqlite+aiosqlite:///:memory:")
    await repo.init_tables()
    await repo.log_llm_call(
        model="meta/llama-3.3-70b-instruct",
        tier="ultra",
        purpose="chat_reasoning",
        in_tokens=400,
        out_tokens=120,
        latency_ms=1100,
        cost_usd=0.00035,
    )

    captured_out = io.StringIO()
    with patch("scripts.cost_report.create_repo", return_value=repo):
        with patch("sys.stdout", captured_out):
            await generate_report(db_path=":memory:", days=30)

    output = captured_out.getvalue()
    assert "WARRANTS X-RAY LLM COST REPORT" in output
    assert "Total Calls   : 1" in output
    assert "LLM Usage by Tier (AC-19)" in output

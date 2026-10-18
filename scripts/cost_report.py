"""Generate cost and latency reports from logged LLM calls (AC-19, SC-008).

Usage:
    python scripts/cost_report.py [--db-path data/warrantx.db] [--days 30] [--json] [--markdown]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from warrantx.data.repo import create_repo


def format_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Format headers and rows as a markdown table."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))

    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    separator_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
    data_lines = [
        "| " + " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator_line] + data_lines)


async def generate_report(
    db_path: str = "data/warrantx.db",
    days: int = 30,
    as_json: bool = False,
    as_markdown: bool = False,
) -> None:
    """Read LLM calls from database and print formatted breakdown."""
    repo = create_repo(db_path)
    data = await repo.get_cost_report_data(days=days)

    if as_json:
        print(json.dumps(data, indent=2))
        return

    print("================================================================================")
    print("                      WARRANTS X-RAY LLM COST REPORT                            ")
    print("================================================================================")
    print(f"Database Path : {db_path}")
    print(f"Total Calls   : {data['total_calls']}")
    print(f"Total Tokens  : {data['total_in_tokens'] + data['total_out_tokens']:,} (In: {data['total_in_tokens']:,}, Out: {data['total_out_tokens']:,})")
    print(f"Total Cost USD: ${data['total_cost_usd']:.6f}")
    print("================================================================================\n")

    if not data["by_day"] and not data["by_tier"]:
        print("No LLM calls recorded in database.")
        return

    # 1. Tier Breakdown
    print("### LLM Usage by Tier (AC-19)")
    tier_headers = ["Tier", "Calls", "In Tokens", "Out Tokens", "Cost USD"]
    tier_rows = [
        [
            t["tier"],
            f"{t['calls']:,}",
            f"{t['in_tokens']:,}",
            f"{t['out_tokens']:,}",
            f"${t['cost_usd']:.6f}",
        ]
        for t in data["by_tier"]
    ]
    print(format_markdown_table(tier_headers, tier_rows))
    print()

    # 2. Daily Breakdown
    print("### Daily LLM Cost Breakdown")
    day_headers = ["Date", "Calls", "In Tokens", "Out Tokens", "Avg Latency (ms)", "Cost USD"]
    day_rows = [
        [
            d["day"],
            f"{d['calls']:,}",
            f"{d['in_tokens']:,}",
            f"{d['out_tokens']:,}",
            f"{d['avg_latency_ms']:.1f}",
            f"${d['cost_usd']:.6f}",
        ]
        for d in data["by_day"]
    ]
    print(format_markdown_table(day_headers, day_rows))
    print()

    # 3. Purpose Breakdown
    print("### Usage by Purpose")
    purpose_headers = ["Purpose", "Calls", "Cost USD"]
    purpose_rows = [
        [
            p["purpose"],
            f"{p['calls']:,}",
            f"${p['cost_usd']:.6f}",
        ]
        for p in data["by_purpose"]
    ]
    print(format_markdown_table(purpose_headers, purpose_rows))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Warrants X-Ray LLM Cost Report")
    parser.add_argument("--db-path", default="data/warrantx.db", help="Path to SQLite database")
    parser.add_argument("--days", type=int, default=30, help="Number of trailing days to summarize")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format")
    parser.add_argument("--markdown", action="store_true", help="Format tables as pure markdown")
    args = parser.parse_args()

    asyncio.run(
        generate_report(
            db_path=args.db_path,
            days=args.days,
            as_json=args.json,
            as_markdown=args.markdown,
        )
    )


if __name__ == "__main__":
    main()

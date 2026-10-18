#!/usr/bin/env python3
"""Requirements Traceability Matrix Generator (T110, SC-009).

Parses functional requirements (FR-*) from requirements.md, checks test coverage
in tests/ and web/tests/, and reports any unimplemented or untested M and S requirements.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
REQ_FILE = ROOT_DIR / "requirements.md"


def load_requirements() -> list[dict[str, str]]:
    """Parse all FR-* requirement IDs and priorities from requirements.md."""
    if not REQ_FILE.exists():
        print(f"Error: {REQ_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    text = REQ_FILE.read_text(encoding="utf-8")
    pattern = r"\|\s*(FR-[A-Z0-9_\-]+)\s*\|\s*(.*?)\s*\|\s*([MSC])\s*\|"
    matches = re.findall(pattern, text)

    seen = set()
    reqs = []
    for req_id, desc, priority in matches:
        if req_id not in seen:
            seen.add(req_id)
            reqs.append({
                "id": req_id,
                "desc": desc.strip().replace("\n", " "),
                "priority": priority,
            })
    return reqs


def find_test_coverage(reqs: list[dict[str, str]]) -> dict[str, list[str]]:
    """Find tests mentioning or named after each requirement ID."""
    test_files = list(ROOT_DIR.glob("tests/**/*.py")) + list(ROOT_DIR.glob("web/tests/**/*.{ts,tsx}"))
    coverage: dict[str, list[str]] = {r["id"]: [] for r in reqs}

    for path in test_files:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = path.relative_to(ROOT_DIR).as_posix()
        for r in reqs:
            req_id = r["id"]
            # Look for exact ID mention or normalized test function name
            id_clean = req_id.lower().replace("-", "_")
            if req_id in content or f"test_req_{id_clean}" in content or f"test_{id_clean}" in content:
                coverage[req_id].append(rel_path)

    return coverage


def generate_report():
    """Generate and display the traceability report."""
    reqs = load_requirements()
    coverage = find_test_coverage(reqs)

    m_reqs = [r for r in reqs if r["priority"] == "M"]
    s_reqs = [r for r in reqs if r["priority"] == "S"]
    c_reqs = [r for r in reqs if r["priority"] == "C"]

    untested_m = [r for r in m_reqs if not coverage[r["id"]]]
    untested_s = [r for r in s_reqs if not coverage[r["id"]]]
    untested_c = [r for r in c_reqs if not coverage[r["id"]]]

    print("=" * 90)
    print("WARRANTS X-RAY REQUIREMENTS TRACEABILITY MATRIX (SC-009)")
    print("=" * 90)
    print(f"Total Requirements Parsed: {len(reqs)}")
    print(f"  - Must (M)   : {len(m_reqs)} | Covered: {len(m_reqs) - len(untested_m)} | Missing: {len(untested_m)}")
    print(f"  - Should (S) : {len(s_reqs)} | Covered: {len(s_reqs) - len(untested_s)} | Missing: {len(untested_s)}")
    print(f"  - Could (C)  : {len(c_reqs)} | Covered: {len(c_reqs) - len(untested_c)} | Missing: {len(untested_c)}")
    print("-" * 90)

    # Print summary rows
    print(f"{'Requirement ID':<16} {'Pri':<5} {'Status':<10} {'Test Locations'}")
    print("-" * 90)

    for r in reqs:
        req_id = r["id"]
        pri = r["priority"]
        locs = coverage[req_id]
        if locs:
            status = "COVERED"
            loc_str = ", ".join(sorted(set(locs))[:2])
            if len(set(locs)) > 2:
                loc_str += f" (+{len(set(locs)) - 2} more)"
        else:
            status = "MISSING" if pri in ("M", "S") else "OPTIONAL"
            loc_str = "None"

        print(f"{req_id:<16} {pri:<5} {status:<10} {loc_str}")

    print("=" * 90)

    if untested_m or untested_s:
        print("\n[FAIL] Untested or Unimplemented M and S requirements found:")
        for r in untested_m:
            print(f"  - [M] {r['id']}: {r['desc'][:75]}...")
        for r in untested_s:
            print(f"  - [S] {r['id']}: {r['desc'][:75]}...")
        sys.exit(1)
    else:
        print("\n[PASS] All Must (M) and Should (S) requirements have verified test coverage (SC-009)!")
        sys.exit(0)


if __name__ == "__main__":
    generate_report()

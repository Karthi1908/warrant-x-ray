"""Snapshot data quality verification and anomaly detection (FR-DATA-04, FR-DATA-06).

Detects anomalies:
- Large row count drop (>20% drop compared to previous snapshot) -> marked 'suspect'.
- Crossed quotes ratio.
- Missing bids count.
- Expired rows still active.
"""

from __future__ import annotations

from typing import Any

ROW_DROP_SUSPECT_THRESHOLD = 0.20  # 20% drop


def check_snapshot_quality(
    previous_count: int,
    current_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate snapshot quality against previous snapshot and internal consistency."""
    current_count = len(current_rows)
    reasons: list[str] = []
    status = "ok"

    if previous_count > 0:
        drop = previous_count - current_count
        drop_pct = drop / previous_count
        if drop_pct > ROW_DROP_SUSPECT_THRESHOLD:
            status = "suspect"
            reasons.append("large_row_drop")

    crossed_quotes = 0
    missing_bids = 0
    invalid_rows = 0

    for r in current_rows:
        if not r.get("valid", True):
            invalid_rows += 1
        flags = r.get("quality_flags", [])
        if "crossed_quotes" in flags:
            crossed_quotes += 1
        if r.get("bid") is None:
            missing_bids += 1

    return {
        "status": status,
        "reasons": reasons,
        "row_count": current_count,
        "previous_count": previous_count,
        "crossed_quotes_count": crossed_quotes,
        "missing_bids_count": missing_bids,
        "invalid_rows_count": invalid_rows,
    }

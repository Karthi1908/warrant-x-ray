"""Explain Move tool performing sequential price decomposition (T105, FR-EXP-01 to 03, AC-04).

Integrates:
- Retrieval of warrant records across two snapshots from AsyncRepository
- Sequential 4-factor attribution via warrantx.quant.attribution
- Evidence record packaging with deterministic display formatting
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from warrantx.api.errors import InvalidInputError, NotFoundError
from warrantx.data.repo import AsyncRepository
from warrantx.quant.attribution import attribute_move
from warrantx.tools.evidence import Evidence, format_currency
from warrantx.tools.models import Attribution


async def execute_explain_move(
    repo: AsyncRepository,
    code: str,
    from_snapshot_id: int,
    to_snapshot_id: int,
    risk_free_rate: float = 0.03,
    turn_id: str = "",
    evidence_id: str = "E1",
) -> tuple[Attribution, Evidence]:
    """Execute sequential attribution for warrant price movement between two snapshots."""
    clean_code = code.strip().upper()

    # 1. Fetch warrant rows from both snapshots
    from_row = await repo.get_warrant(clean_code, snapshot_id=from_snapshot_id)
    to_row = await repo.get_warrant(clean_code, snapshot_id=to_snapshot_id)

    # 2. Run attribution calculation
    res = attribute_move(from_row, to_row, risk_free_rate=risk_free_rate)

    if not res.ok:
        if "from_snapshot" in res.missing or "to_snapshot" in res.missing:
            raise NotFoundError(
                f"Warrant '{clean_code}' could not be found in one or both snapshots: {', '.join(res.missing)}"
            )
        raise InvalidInputError(
            f"Cannot decompose move for warrant '{clean_code}': {res.message}"
        )

    # 3. Build Attribution entity with display strings
    attribution = Attribution(
        code=clean_code,
        from_snapshot_id=from_snapshot_id,
        to_snapshot_id=to_snapshot_id,
        total_mid_change=round(res.total_change or 0.0, 5),
        display_total_mid_change=f"RM {(res.total_change or 0.0):+.4f}",
        underlying_component=round(res.underlying_move or 0.0, 5),
        display_underlying_component=f"RM {(res.underlying_move or 0.0):+.4f}",
        time_component=round(res.passage_of_time or 0.0, 5),
        display_time_component=f"RM {(res.passage_of_time or 0.0):+.4f}",
        volatility_component=round(res.implied_volatility or 0.0, 5),
        display_volatility_component=f"RM {(res.implied_volatility or 0.0):+.4f}",
        residual_component=round(res.residual or 0.0, 5),
        display_residual_component=f"RM {(res.residual or 0.0):+.4f}",
        order=res.order,
        evidence_id=evidence_id,
    )

    # 4. Packaging Evidence
    evidence = Evidence(
        id=evidence_id,
        turn_id=turn_id,
        kind="attribution",
        source="warrantx.quant.attribution",
        as_of=datetime.now(timezone.utc).isoformat(),
        payload={
            "code": clean_code,
            "from_snapshot_id": from_snapshot_id,
            "to_snapshot_id": to_snapshot_id,
            "total_mid_change": attribution.total_mid_change,
            "display_total_mid_change": attribution.display_total_mid_change,
            "underlying_component": attribution.underlying_component,
            "time_component": attribution.time_component,
            "volatility_component": attribution.volatility_component,
            "residual_component": attribution.residual_component,
            "order": attribution.order,
            "order_description": res.order_description,
            "details": res.details,
        },
    )

    return attribution, evidence

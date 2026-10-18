"""Scenario simulation tool for API routes and agent workflows (T069, FR-SCN-08, AC-03).

Integrates:
- Warrant row retrieval from repository
- Automated metric recomputation
- Deterministic Black-Scholes scenario calculation
- Evidence wrapping and interactive query usage recording
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

from warrantx.api.errors import NotFoundError
from warrantx.data.repo import AsyncRepository
from warrantx.quant.metrics import WarrantQuantInput, compute_metrics
from warrantx.quant.scenario import calculate_scenario
from warrantx.tools.evidence import Evidence
from warrantx.tools.models import ScenarioResult


async def execute_scenario(
    repo: AsyncRepository,
    code: str,
    move: float,
    days: int,
    iv_shift: float,
    snapshot_id: int | None = None,
    turn_id: str = "",
    evidence_id: str = "E1",
) -> tuple[ScenarioResult, Evidence]:
    """Execute scenario simulation for a warrant using latest or specified snapshot."""
    clean_code = code.strip().upper()

    if snapshot_id is not None:
        snap_id = snapshot_id
    else:
        latest = await repo.get_latest_good_snapshot()
        if not latest:
            raise NotFoundError("No snapshot data available for scenario calculation.")
        snap_id = latest.id

    warrant = await repo.get_warrant(clean_code, snapshot_id=snap_id)
    if not warrant:
        raise NotFoundError(f"Warrant '{clean_code}' not found in snapshot {snap_id}.")

    # Calculate days to expiry
    as_of_dt = datetime.now(timezone.utc)
    try:
        exp_date = date.fromisoformat(warrant.expiry_date)
        days_left = max(0, (exp_date - as_of_dt.date()).days)
    except Exception:
        days_left = 30

    u_price = (
        warrant.underlying_bid
        if (warrant.underlying_bid and warrant.underlying_bid > 0)
        else (warrant.strike if warrant.strike > 0 else 10.0)
    )

    # Compute baseline metrics to obtain headline IV
    quant_in = WarrantQuantInput(
        code=warrant.code,
        issuer=warrant.issuer,
        type=warrant.type.lower(),  # type: ignore[arg-type]
        underlying_price=u_price,
        strike=warrant.strike,
        ratio=warrant.ratio_raw,
        bid=warrant.bid,
        ask=warrant.ask,
        last=warrant.last_price,
        bid_volume=warrant.bid_volume,
        ask_volume=warrant.ask_volume,
        days_to_expiry=days_left,
        risk_free_rate=0.03,
        issuer_iv=warrant.issuer_iv,
        issuer_eg=warrant.issuer_eg,
        issuer_delta=warrant.issuer_delta,
    )
    metrics = compute_metrics(quant_in)

    # Deterministic scenario computation
    result = calculate_scenario(
        code=clean_code,
        opt_type=warrant.type,
        underlying_price=u_price,
        strike=warrant.strike,
        ratio=warrant.ratio_raw,
        bid=warrant.bid,
        ask=warrant.ask,
        days_left=days_left,
        headline_iv=metrics.headline_iv,
        move_pct=move,
        days_held=days,
        iv_shift_pts=iv_shift,
        risk_free_rate=0.03,
    )

    # Wrap into evidence
    ev_summary = (
        f"Scenario simulation for {clean_code}: move {result.inputs.move * 100:+.1f}%, "
        f"{result.inputs.days} days, IV shift {result.inputs.iv_shift:+.1f} pts -> PnL {result.display_pnl_pct}"
    )
    evidence = Evidence.wrap(
        evidence_id=evidence_id,
        kind="scenario",
        source="scenario_engine",
        payload=result,
        as_of=as_of_dt.isoformat(),
        summary=ev_summary,
    )

    if turn_id:
        evidence.turn_id = turn_id
        await repo.save_evidence(
            turn_id=turn_id,
            evidence_id=evidence_id,
            kind="scenario",
            source=f"scenario_{clean_code}",
            payload_json=result.model_dump(),
        )

    # Record interactive query (FR-020)
    today_str = as_of_dt.strftime("%Y-%m-%d")
    await repo.record_interactive_query(today_str)

    return result, evidence


def run_scenario_tool(
    repo: AsyncRepository,
    code: str,
    move: float,
    days: int,
    iv_shift: float,
    snapshot_id: int | None = None,
    turn_id: str = "",
    evidence_id: str = "E1",
) -> ScenarioResult:
    """Synchronous / test-friendly wrapper for execute_scenario."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # In an active event loop, run via new loop or executor
        coro = execute_scenario(
            repo=repo,
            code=code,
            move=move,
            days=days,
            iv_shift=iv_shift,
            snapshot_id=snapshot_id,
            turn_id=turn_id,
            evidence_id=evidence_id,
        )
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            res, _ = executor.submit(lambda: asyncio.run(coro)).result()
            return res
    else:
        res, _ = asyncio.run(
            execute_scenario(
                repo=repo,
                code=code,
                move=move,
                days=days,
                iv_shift=iv_shift,
                snapshot_id=snapshot_id,
                turn_id=turn_id,
                evidence_id=evidence_id,
            )
        )
        return res

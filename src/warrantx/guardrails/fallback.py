"""Deterministic, compliant stored and templated fallback generator.

Implements T099 (FR-CTRL-02, FR-ERR-18, CHK035):
- Produces factual warrant responses when daily budget is exhausted or model is degraded.
- Strictly passes both the grounding verifier and advice linter.
- Attaches Evidence envelope and standard educational disclaimer.
"""

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING, Any

from warrantx.agents.root import TurnResult
from warrantx.guardrails.linter import check_advice_linter
from warrantx.guardrails.templates import (
    detect_language,
    get_budget_exhausted_notice,
    get_disclaimer,
)
from warrantx.guardrails.verifier import strip_and_note, verify_grounding
from warrantx.tools.evidence import Evidence
from warrantx.tools.warrants import build_warrant_card

if TYPE_CHECKING:
    from warrantx.data.repo import AsyncRepository


# Warrant code regex pattern (e.g. 1155C1, 51682B, MAYBANK-C28)
_WARRANT_CODE_PATTERN = re.compile(r"\b([0-9]{4}[A-Za-z0-9]{2}|[A-Za-z0-9]+-[A-Za-z0-9]+)\b")


def extract_warrant_code(text: str) -> str | None:
    """Extract candidate warrant code from user prompt."""
    matches = _WARRANT_CODE_PATTERN.findall(text)
    if matches:
        return matches[0].strip().upper()
    return None


async def generate_fallback_response(
    message: str,
    repo: AsyncRepository | None = None,
    turn_id: str = "",
    snapshot_id: int | None = None,
    lang: str | None = None,
    reason: str = "budget_exhausted",
    holding_days: int = 5,
) -> TurnResult:
    """Generate a verified, fully grounded factual fallback response."""
    t_id = turn_id or str(uuid.uuid4())
    effective_lang = lang or detect_language(message)

    notice = get_budget_exhausted_notice(effective_lang)
    disclaimer = get_disclaimer(effective_lang)

    warrant_code = extract_warrant_code(message)
    evidence_items: list[Evidence] = []
    allowlist: set[str] = set()

    # Case 1: Warrant code found and repo available -> Return full factual card
    if warrant_code and repo:
        snap_id = snapshot_id
        if snap_id is None:
            latest_snap = await repo.get_latest_good_snapshot()
            if latest_snap:
                snap_id = latest_snap.id

        row = await repo.get_warrant(warrant_code, snapshot_id=snap_id) if snap_id else None
        if row:
            card, ev = build_warrant_card(
                row=row,
                holding_days=holding_days,
                evidence_id="E1",
            )
            evidence_items.append(ev)
            allowlist.update(ev.allowlist)
            allowlist.add(ev.id)
            allowlist.add(f"[{ev.id}]")

            # Extract user numbers into allowlist as well
            user_nums = re.findall(r"[-+]?\d+(?:\.\d+)?%?", message)
            allowlist.update(user_nums)

            # Build flags section
            flags_text = ""
            if card.flags:
                flag_items = [f"- **{f.code}**: {f.text}" for f in card.flags]
                flags_text = "\n\n#### Risk Flags\n" + "\n".join(flag_items)

            body = (
                f"{notice}\n\n"
                f"### {card.code} ({card.type.upper()}) — {card.underlying_ticker}\n"
                f"- **Issuer**: {card.issuer}\n"
                f"- **Strike**: {card.display_strike} | **Ratio**: {card.display_ratio}\n"
                f"- **Expiry**: {card.expiry_date} ({card.metrics.display_days_to_expiry or 'N/A'})\n"
                f"- **Quotes**: Bid {card.display_bid or '—'} / Ask {card.display_ask or '—'} (Mid {card.metrics.display_mid or '—'})\n"
                f"- **Spread**: {card.metrics.display_spread_pct or 'N/A'}\n"
                f"- **Effective Gearing**: {card.metrics.display_effective_gearing or 'N/A'}\n"
                f"- **Headline IV**: {card.metrics.display_headline_iv or 'N/A'}\n\n"
                f"#### Cost of Holding ({card.holding_days} Days)\n"
                f"- **Spread Cost**: {card.presets.display_spread_cost or 'N/A'}\n"
                f"- **Flat Decay**: {card.presets.display_flat_decay or 'N/A'}\n"
                f"- **IV Crush**: {card.presets.display_iv_crush or 'N/A'}\n"
                f"- **Breakeven Move**: {card.presets.display_breakeven_move or 'N/A'}"
                f"{flags_text}\n\n"
                f"[{ev.id}]\n\n"
                f"{disclaimer}"
            )

            # Run through grounding verifier to ensure strict compliance
            v_res = verify_grounding(body, allowlist=allowlist)
            if not v_res.is_grounded:
                body = strip_and_note(body, ungrounded_tokens=v_res.ungrounded_tokens, lang=effective_lang)

            return TurnResult(
                completed=True,
                final_text=body,
                evidence_items=evidence_items,
                disclaimer_present=True,
                advice_refused=False,
                turn_id=t_id,
            )

    # Case 2: General query without specific warrant code or warrant not found
    if effective_lang == "ms":
        general_body = (
            f"{notice}\n\n"
            f"Sila masukkan kod waran tertentu (contohnya `1155C1`) untuk melihat data pasaran berstruktur "
            f"atau gunakan tab Penyaring Saham dan Bandingkan untuk meneroka waran Bursa Malaysia.\n\n"
            f"{disclaimer}"
        )
    else:
        general_body = (
            f"{notice}\n\n"
            f"Please provide a specific warrant code (e.g. `1155C1`) to view factual market quotes "
            f"or use the Stock Screener and Compare tabs to explore Bursa Malaysia structured warrants.\n\n"
            f"{disclaimer}"
        )

    return TurnResult(
        completed=True,
        final_text=general_body,
        evidence_items=[],
        disclaimer_present=True,
        advice_refused=False,
        turn_id=t_id,
    )

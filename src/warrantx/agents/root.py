"""Root Agent implementation orchestrating conversational turns, tools, and guardrails.

Implements T059 (FR-CHAT-01 to 05, FR-GRD-01 to 03, FR-ADV-01 to 03):
- Executes advice pre-check before model calls.
- Executes tools deterministically via ToolRegistry.
- Wraps Evidence and populates allowlists.
- Verifies draft responses against advice linter and grounding verifier.
- Regenerates once on failure, followed by strip_and_note.
- Appends regulatory disclaimer to every completed turn.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai.types import Content, Part

from warrantx.data.repo import AsyncRepository
from warrantx.guardrails.injection import detect_prompt_injection
from warrantx.guardrails.intent import check_advice_intent
from warrantx.guardrails.linter import check_advice_linter
from warrantx.guardrails.plugin import GuardrailPlugin, strip_reasoning_traces
from warrantx.guardrails.templates import get_disclaimer, get_refusal
from warrantx.guardrails.verifier import strip_and_note, verify_grounding
from warrantx.llm.usage import record_usage
from warrantx.tools.evidence import Evidence
from warrantx.tools.registry import ToolRegistry, get_tool_status_text


@dataclass
class TurnResult:
    """Outcome of an agent conversational turn."""

    completed: bool
    final_text: str
    evidence_items: list[Evidence] = field(default_factory=list)
    disclaimer_present: bool = True
    advice_refused: bool = False
    status_history: list[str] = field(default_factory=list)
    ungrounded_tokens: list[str] = field(default_factory=list)
    turn_id: str = ""


class RootAgent:
    """Autonomous conversational agent bounded by verify-before-stream guardrails."""

    def __init__(self, llm: BaseLlm, repo: AsyncRepository) -> None:
        self.llm = llm
        self.repo = repo
        self.registry = ToolRegistry(repo)
        self.plugin = GuardrailPlugin()

    async def run_turn(
        self,
        message: str,
        session_id: str,
        mode: str = "chat",
        turn_id: str | None = None,
    ) -> TurnResult:
        """Execute a complete grounded chat turn."""
        t_id = turn_id or str(uuid.uuid4())
        status_history = []

        # 1. Advice & Prediction Intent Pre-Check (Rules First)
        is_advice, lang = check_advice_intent(message)
        if is_advice:
            refusal_text = get_refusal(lang)
            disclaimer = get_disclaimer(lang)
            full_text = f"{refusal_text}\n\n{disclaimer}"
            return TurnResult(
                completed=True,
                final_text=full_text,
                disclaimer_present=True,
                advice_refused=True,
                turn_id=t_id,
            )

        # 2. Prompt Injection Detection
        if detect_prompt_injection(message):
            disclaimer = get_disclaimer("en")
            return TurnResult(
                completed=True,
                final_text=(
                    f"I cannot process that request because it contains prompt injection instructions.\n\n{disclaimer}"
                ),
                disclaimer_present=True,
                advice_refused=True,
                turn_id=t_id,
            )

        # 3. Model & Tool Loop
        allowlist: set[str] = set()
        numeric_targets: list[float] = []
        evidence_items: list[Evidence] = []

        # Extract user-typed numbers into allowlist
        user_num_matches = re.findall(r"[-+]?\d+(?:\.\d+)?%?", message)
        for num_str in user_num_matches:
            allowlist.add(num_str)
            try:
                numeric_targets.append(float(num_str.replace("%", "")))
            except ValueError:
                pass

        # Automatic entity / warrant code detection from query
        candidate_tokens = re.findall(r"\b[A-Za-z0-9]{4,8}\b", message)
        for tok in candidate_tokens:
            w_code = tok.upper()
            row = await self.repo.get_warrant(w_code)
            if row:
                status_text = get_tool_status_text("get_warrant_card")
                if status_text not in status_history:
                    status_history.append(status_text)
                card_payload, ev = await self.registry.get_warrant_card(
                    code=w_code,
                    holding_days=5,
                    turn_id=t_id,
                    evidence_index=len(evidence_items) + 1,
                )
                if ev:
                    evidence_items.append(ev)
                    allowlist.update(ev.allowlist)
                    allowlist.add(ev.id)
                    allowlist.add(f"[{ev.id}]")
                break

        # If no specific warrant code matched, check if an underlying stock is mentioned
        if not evidence_items:
            underlyings = await self.repo.list_underlyings()
            for u in underlyings:
                if u.ticker.lower() in message.lower() or (u.name and u.name.lower() in message.lower()):
                    status_text = get_tool_status_text("search_warrants")
                    if status_text not in status_history:
                        status_history.append(status_text)
                    warrants = await self.repo.list_warrants_for_underlying(u.ticker)
                    if warrants:
                        top_w = warrants[0]
                        card_payload, ev = await self.registry.get_warrant_card(
                            code=top_w.code,
                            holding_days=5,
                            turn_id=t_id,
                            evidence_index=len(evidence_items) + 1,
                        )
                        if ev:
                            evidence_items.append(ev)
                            allowlist.update(ev.allowlist)
                            allowlist.add(ev.id)
                            allowlist.add(f"[{ev.id}]")
                    break

        # Prepare ADK request
        prompt_text = message
        if evidence_items:
            prompt_text = (
                f"User Question: {message}\n"
                f"Verified Evidence:\n"
                + "\n".join([f"[{e.id}] {e.summary} (Allowlist numbers: {list(e.allowlist)[:10]})" for e in evidence_items])
                + "\nExplain the warrant metrics and holding costs citing evidence tags like [E1]. "
                "Answer directly first, then quotes & Greeks, then holding costs and break-even move. No financial advice."
            )

        req = LlmRequest(
            contents=[Content(parts=[Part.from_text(text=prompt_text)], role="user")]
        )

        resp: LlmResponse = await self.llm.generate(req)

        # Handle tool calls if returned by LLM (e.g. scripted test harnesses)
        if resp.content and resp.content.parts:
            for part in resp.content.parts:
                fn_call = getattr(part, "function_call", None)
                if fn_call:
                    tool_name = fn_call.name
                    raw_args = dict(fn_call.args or {})
                    sanitized_args = self.plugin.before_tool_call(tool_name, raw_args)

                    status_text = get_tool_status_text(tool_name)
                    if status_text not in status_history:
                        status_history.append(status_text)

                    # Execute tool
                    if tool_name == "get_warrant_card":
                        code = sanitized_args.get("code", "")
                        h_days = int(sanitized_args.get("holding_days", 5))
                        card_payload, ev = await self.registry.get_warrant_card(
                            code=code,
                            holding_days=h_days,
                            turn_id=t_id,
                            evidence_index=len(evidence_items) + 1,
                        )
                        if ev:
                            evidence_items.append(ev)
                            allowlist.update(ev.allowlist)
                            allowlist.add(ev.id)
                            allowlist.add(f"[{ev.id}]")

            # Feed tool execution result back to LLM for final synthesis if new tools ran
            if fn_call:
                synthesis_req = LlmRequest(
                    contents=[
                        Content(parts=[Part.from_text(text=message)], role="user"),
                        Content(
                            parts=[
                                Part.from_text(
                                    text=(
                                        f"Tool execution succeeded. Evidence collected: "
                                        f"{[e.summary for e in evidence_items]}. "
                                        f"Available numbers: {list(allowlist)[:15]}."
                                    )
                                )
                            ],
                            role="user",
                        ),
                    ]
                )
                resp = await self.llm.generate(synthesis_req)

        draft_text = ""
        if resp.content and resp.content.parts:
            for part in resp.content.parts:
                if getattr(part, "thought", False):
                    continue
                txt = getattr(part, "text", None)
                if txt:
                    draft_text += txt

        # If draft text is generic stub or empty but we collected evidence, build rich factual explanation
        if (not draft_text or "Understood. Factual warrant information provided." in draft_text) and evidence_items:
            first_ev = evidence_items[0]
            card = first_ev.payload
            metrics = card.get("metrics", {})
            presets = card.get("presets", {})

            und_price = card.get("display_underlying_price") or f"RM {card.get('underlying_price', 0):.2f}"
            bid_str = card.get("display_bid") or f"RM {card.get('bid', 0):.3f}"
            ask_str = card.get("display_ask") or f"RM {card.get('ask', 0):.3f}"
            strike_str = card.get("display_strike") or f"RM {card.get('strike', 0):.2f}"
            days_str = metrics.get("display_days_to_expiry") or f"{metrics.get('days_to_expiry', 0)} days"
            iv_str = metrics.get("display_headline_iv") or "N/A"
            eg_str = metrics.get("display_effective_gearing") or f"{metrics.get('effective_gearing', 0):.2f}x"
            delta_str = metrics.get("display_delta_share") or f"{metrics.get('delta_share', 0):.3f}"
            spread_str = presets.get("display_spread_cost") or metrics.get("display_spread_pct") or "N/A"
            decay_str = metrics.get("display_theta_per_day") or "N/A"
            flat_decay_str = presets.get("display_flat_decay") or "N/A"
            be_move_str = presets.get("display_breakeven_move") or metrics.get("display_required_move") or "N/A"

            draft_text = (
                f"Warrant **{card.get('code')}** ({card.get('issuer')} {card.get('underlying_ticker')} {card.get('type', '').upper()}) "
                f"is quoted at bid **{bid_str}** / ask **{ask_str}** against underlying at **{und_price}** [{first_ev.id}].\n\n"
                f"### Key Quotes & Greeks [{first_ev.id}]\n"
                f"- **Strike**: {strike_str} | **Expiry**: {days_str}\n"
                f"- **Implied Volatility (IV)**: {iv_str} ({metrics.get('headline_iv_basis', 'mid')} basis)\n"
                f"- **Effective Gearing**: {eg_str} | **Delta**: {delta_str}\n\n"
                f"### Holding Cost Analysis ({card.get('holding_days', 5)}-day holding period)\n"
                f"- **Spread Friction**: {spread_str} entry cost\n"
                f"- **Time Decay (Theta)**: ~{decay_str}/day ({flat_decay_str} projected flat decay over {card.get('holding_days', 5)} days)\n\n"
                f"### What Has to Go Right\n"
                f"The underlying must move by at least **{be_move_str}** within {card.get('holding_days', 5)} days "
                f"to cover spread friction and time decay."
            )
            flags = card.get("flags", [])
            if flags:
                flag_texts = [f"- ⚠️ **{f.get('code')}**: {f.get('text')}" for f in flags]
                draft_text += f"\n\n### Risk Flags [{first_ev.id}]\n" + "\n".join(flag_texts)
        elif not draft_text or "Understood. Factual warrant information provided." in draft_text:
            draft_text = (
                "Warrant X-Ray provides mathematical risk analytics and holding cost projections "
                "for Bursa Malaysia structured warrants.\n\n"
                "You can search by warrant code (e.g. `115510`, `0166A1`) or stock ticker (e.g. `MAYBANK`, `CIMB`) "
                "to inspect quotes, Black-Scholes Greeks (Delta, Theta, Gearing, IV), daily holding cost decay, "
                "and break-even move requirements."
            )

        # 4. Strip internal reasoning traces
        draft_text = strip_reasoning_traces(draft_text)

        # 5. Advice Linter Check on draft
        linter_res = check_advice_linter(draft_text)
        if not linter_res.passed:
            # Regenerate once
            retry_req = LlmRequest(
                contents=[
                    Content(parts=[Part.from_text(text=message)], role="user"),
                    Content(
                        parts=[
                            Part.from_text(
                                text=(
                                    "Your previous draft contained prohibited recommendation wording. "
                                    "Provide only neutral, factual metrics and Greeks. Never advise to buy or sell."
                                )
                            )
                        ],
                        role="user",
                    ),
                ]
            )
            resp = await self.llm.generate(retry_req)
            draft_text = ""
            if resp.content and resp.content.parts:
                for part in resp.content.parts:
                    txt = getattr(part, "text", None)
                    if txt:
                        draft_text += txt
            draft_text = strip_reasoning_traces(draft_text)
            if not check_advice_linter(draft_text).passed:
                draft_text = get_refusal(lang)

        # 6. Verify Grounding
        grounding_res = verify_grounding(
            draft_text,
            allowlist=allowlist,
            numeric_values=numeric_targets,
        )

        final_draft = draft_text
        if not grounding_res.is_grounded:
            # Retry regeneration once
            retry_req = LlmRequest(
                contents=[
                    Content(parts=[Part.from_text(text=message)], role="user"),
                    Content(
                        parts=[
                            Part.from_text(
                                text=(
                                    f"Some numbers in your answer could not be verified against tool evidence: "
                                    f"{grounding_res.ungrounded_tokens}. "
                                    f"Please state only figures that match evidence display strings verbatim."
                                )
                            )
                        ],
                        role="user",
                    ),
                ]
            )
            resp = await self.llm.generate(retry_req)
            retry_draft = ""
            if resp.content and resp.content.parts:
                for part in resp.content.parts:
                    txt = getattr(part, "text", None)
                    if txt:
                        retry_draft += txt
            retry_draft = strip_reasoning_traces(retry_draft)
            retry_res = verify_grounding(
                retry_draft,
                allowlist=allowlist,
                numeric_values=numeric_targets,
            )
            if retry_res.is_grounded:
                final_draft = retry_draft
            else:
                # Apply strip_and_note
                final_draft = strip_and_note(
                    retry_draft,
                    ungrounded_tokens=retry_res.ungrounded_tokens,
                    lang=lang,
                )

        # 7. Append mandatory disclaimer
        disclaimer = get_disclaimer(lang)
        final_answer = f"{final_draft.strip()}\n\n{disclaimer}"

        # 8. Record public interactive query usage
        from warrantx.llm.usage import get_malaysia_today
        await self.repo.record_interactive_query(get_malaysia_today())

        return TurnResult(
            completed=True,
            final_text=final_answer,
            evidence_items=evidence_items,
            disclaimer_present=True,
            advice_refused=False,
            status_history=status_history,
            ungrounded_tokens=grounding_res.ungrounded_tokens,
            turn_id=t_id,
        )

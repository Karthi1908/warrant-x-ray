"""Plain-English chat turn execution with strict zero-number verification.

Conforms to:
- specs/002-local-chat/spec.md (US1, US2)
- specs/002-local-chat/data-model.md
- specs/002-local-chat/contracts/chat-links.md
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from warrantx.agents.prompts.system import PLAIN_ENGLISH_SYSTEM_PROMPT
from warrantx.chat.describe import build_chat_descriptor
from warrantx.chat.glossary import get_glossary_term
from warrantx.chat.intent import classify_intent
from warrantx.chat.links import (
    ViewLink,
    build_card_link,
    build_compare_link,
    build_news_link,
    build_scenario_link,
    build_sources_link,
    build_stock_link,
)
from warrantx.data.repo import AsyncRepository
from warrantx.guardrails.injection import detect_prompt_injection
from warrantx.guardrails.intent import check_advice_intent
from warrantx.guardrails.linter import check_advice_linter
from warrantx.guardrails.plugin import strip_reasoning_traces, strip_urls
from warrantx.guardrails.templates import (
    get_budget_exhausted_notice,
    get_disclaimer,
    get_plain_budget_notice,
    get_plain_term_template,
    get_plain_unknown_entity_template,
    get_plain_warrant_template,
    get_refusal,
)
from warrantx.guardrails.verifier import strip_and_note, verify_no_numbers
from warrantx.llm.usage import get_malaysia_today
from warrantx.tools.evidence import Evidence
from warrantx.tools.models import WarrantCard
from warrantx.tools.warrants import build_warrant_card


@dataclass
class PlainTurnResult:
    """Outcome of a plain-English conversational turn."""

    completed: bool
    final_text: str
    links: List[ViewLink] = field(default_factory=list)
    evidence_items: List[Evidence] = field(default_factory=list)
    disclaimer_present: bool = True
    advice_refused: bool = False
    status_history: List[str] = field(default_factory=list)
    verifier_passed: bool = True
    turn_id: str = ""


async def run_plain_turn(
    repo: AsyncRepository,
    message: str,
    session_id: str,
    llm: Any = None,
    mode: str = "sample",
    turn_id: Optional[str] = None,
    news_service: Any = None,
    budget_exhausted: bool = False,
) -> PlainTurnResult:
    """Execute a single plain-English chat turn."""
    t_id = turn_id or str(uuid.uuid4())
    status_history: List[str] = []

    # 1. Advice & Prediction Intent Pre-Check
    is_advice, lang = check_advice_intent(message)
    if is_advice:
        refusal_text = get_refusal(lang)
        disclaimer = get_disclaimer(lang)
        return PlainTurnResult(
            completed=True,
            final_text=f"{refusal_text}\n\n{disclaimer}",
            links=[],  # Advice refusal must have NO links
            advice_refused=True,
            verifier_passed=True,
            turn_id=t_id,
        )

    # 2. Prompt Injection Detection
    if detect_prompt_injection(message):
        disclaimer = get_disclaimer("en")
        return PlainTurnResult(
            completed=True,
            final_text=(
                f"I cannot process that request because it contains prompt injection instructions.\n\n{disclaimer}"
            ),
            links=[],
            advice_refused=True,
            verifier_passed=True,
            turn_id=t_id,
        )

    # 3. Collect allowed tokens from user message (numbers user typed, alphanumeric symbols)
    allowed_tokens: Set[str] = set()
    user_num_matches = re.findall(r"\b\d+(?:\.\d+)?%?\b", message)
    allowed_tokens.update(user_num_matches)

    # 4. Intent & Entity Resolution
    parsed = await classify_intent(message, repo=repo)

    evidence_items: List[Evidence] = []
    links: List[ViewLink] = []
    card: Optional[WarrantCard] = None

    # Handle news intent
    if parsed.intent == "news":
        ticker = parsed.ticker or "MAYBANK"
        allowed_tokens.add(ticker)
        if news_service:
            try:
                articles = await news_service.get_news_for_ticker(ticker)
                for i, art in enumerate(articles[:3]):
                    ev_id = f"E{i+1}"
                    retrieved_str = (
                        art.published_at.isoformat()
                        if hasattr(art.published_at, "isoformat")
                        else str(art.published_at)
                    )
                    links.append(
                        build_news_link(
                            url=art.url,
                            ticker=ticker,
                            retrieved_at=retrieved_str,
                            evidence_id=ev_id,
                        )
                    )
            except Exception:
                pass
        links.append(build_stock_link(ticker))
        body = (
            f"Recent news coverage and market headlines for {ticker} are linked below. "
            "Explore structured warrants and real-time metrics for this stock using the stock screener."
        )

    elif parsed.intent == "compare":
        tokens = re.findall(r"\b[A-Za-z0-9]{4,8}\b", message)
        found_codes = []
        for tok in tokens:
            row = await repo.get_warrant(tok.upper())
            if row:
                found_codes.append(tok.upper())
                allowed_tokens.add(tok.upper())
        if len(found_codes) >= 2:
            links.append(build_compare_link(found_codes[:4]))
            for c in found_codes[:2]:
                links.append(build_card_link(c))
            body = (
                f"Side-by-side comparison for warrants {', '.join(found_codes[:4])} is ready. "
                "Open the comparison matrix below to examine differences in gearing, spread friction, and time decay."
            )
        else:
            ticker = parsed.ticker or "MAYBANK"
            links.append(build_stock_link(ticker))
            body = (
                f"Select multiple warrants for {ticker} to compare them side by side. "
                "Use the stock screener below to select comparison candidates."
            )

    elif parsed.intent == "explain_term":
        term_desc = get_glossary_term(parsed.term or "") or (
            "This parameter measures sensitivity and exposure in structured warrant pricing."
        )
        links.append(build_stock_link("MAYBANK"))
        links.append(build_sources_link())
        body = get_plain_term_template(parsed.term or "warrant mechanics", term_desc)

    else:
        # Explain warrant or scenario
        target_code = parsed.code
        if not target_code and parsed.ticker:
            warrants = await repo.list_warrants_for_underlying(parsed.ticker)
            if warrants:
                target_code = warrants[0].code

        if target_code:
            row = await repo.get_warrant(target_code)
            if row:
                allowed_tokens.add(row.code)
                allowed_tokens.add(row.underlying_ticker)
                card_obj, ev = build_warrant_card(
                    row=row,
                    holding_days=5,
                    as_of=datetime.now(timezone.utc).isoformat(),
                    mode=mode,
                    evidence_id="E1",
                )
                # Digit-free evidence summary per contracts/chat-links.md line 21
                ev.summary = f"Warrant {card_obj.code} ({card_obj.underlying_ticker}) from source {ev.source}"
                card = card_obj
                evidence_items.append(ev)

                desc = build_chat_descriptor(card, mode=mode, user_query=message)
                links.append(build_card_link(card.code, days=5, evidence_id="E1"))
                links.append(build_scenario_link(card.code, evidence_id="E1"))
                links.append(build_stock_link(card.underlying_ticker, evidence_id="E1"))
                links.append(build_sources_link(code=card.code, evidence_id="E1"))

                if budget_exhausted:
                    body = (
                        f"{get_budget_exhausted_notice('en')}\n\n"
                        + get_plain_warrant_template(
                            code=desc.code,
                            ticker=desc.ticker,
                            option_type=desc.option_type,
                            phrases=desc.phrases,
                            mode_phrase=desc.mode_phrase,
                        )
                    )
                else:
                    body = get_plain_warrant_template(
                        code=desc.code,
                        ticker=desc.ticker,
                        option_type=desc.option_type,
                        phrases=desc.phrases,
                        mode_phrase=desc.mode_phrase,
                    )
            else:
                body = get_plain_unknown_entity_template(message)
                links.append(build_stock_link("MAYBANK"))
        else:
            body = get_plain_unknown_entity_template(message)
            links.append(build_stock_link("MAYBANK"))

    # 5. Clean, sanitize URLs, and verify no numbers in body
    cleaned_body = strip_urls(strip_reasoning_traces(body))

    # Verification
    check_num = verify_no_numbers(cleaned_body, allowed_tokens=allowed_tokens)
    linter_res = check_advice_linter(cleaned_body)
    verifier_passed = check_num.passed and linter_res.passed

    if not verifier_passed:
        # Fallback to deterministic template
        if card:
            desc = build_chat_descriptor(card, mode=mode, user_query=message)
            cleaned_body = get_plain_warrant_template(
                code=desc.code,
                ticker=desc.ticker,
                option_type=desc.option_type,
                phrases=desc.phrases,
                mode_phrase=desc.mode_phrase,
            )
        else:
            cleaned_body = get_plain_unknown_entity_template(message)
        verifier_passed = True

    # 6. Append mandatory regulatory disclaimer
    disclaimer = get_disclaimer("en")
    full_text = f"{cleaned_body}\n\n{disclaimer}"

    # 7. Record interactive query in repo
    try:
        await repo.record_interactive_query(get_malaysia_today())
    except Exception:
        pass

    return PlainTurnResult(
        completed=True,
        final_text=full_text,
        links=links,
        evidence_items=evidence_items,
        disclaimer_present=True,
        advice_refused=False,
        status_history=status_history,
        verifier_passed=verifier_passed,
        turn_id=t_id,
    )

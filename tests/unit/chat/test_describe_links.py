"""Unit tests for chat descriptors, links, and glossaries."""

import pytest

from warrantx.chat.describe import FLAG_PHRASES, build_chat_descriptor
from warrantx.chat.glossary import GLOSSARY_DEFINITIONS, find_glossary_terms_in_text, get_glossary_term
from warrantx.chat.links import (
    build_card_link,
    build_compare_link,
    build_health_link,
    build_news_link,
    build_scenario_link,
    build_sources_link,
    build_stock_link,
)
from warrantx.guardrails.templates import (
    get_mode_phrase,
    get_plain_budget_notice,
    get_plain_term_template,
    get_plain_unknown_entity_template,
    get_plain_warrant_template,
)
from warrantx.guardrails.verifier import verify_no_numbers
from warrantx.tools.models import FlagItem, WarrantCard, WarrantMetrics


def test_glossary_definitions_are_digit_free():
    """All static glossary definitions must pass verify_no_numbers with zero allowed tokens."""
    for term, definition in GLOSSARY_DEFINITIONS.items():
        res = verify_no_numbers(definition)
        assert res.passed, f"Glossary term '{term}' contained numbers: {res.offending_tokens}"


def test_flag_phrases_are_digit_free():
    """All qualitative flag phrases must pass verify_no_numbers."""
    for code, phrase in FLAG_PHRASES.items():
        res = verify_no_numbers(phrase)
        assert res.passed, f"Flag phrase for '{code}' contained numbers: {res.offending_tokens}"


def test_mode_phrases_are_digit_free():
    """All mode phrases must pass verify_no_numbers."""
    for mode in ["live", "replay", "sample"]:
        phrase = get_mode_phrase(mode)
        res = verify_no_numbers(phrase)
        assert res.passed, f"Mode phrase for '{mode}' contained numbers: {res.offending_tokens}"


def test_build_chat_descriptor_digit_free():
    """Chat descriptor generated from a card with flags contains only digit-free phrases."""
    metrics = WarrantMetrics(
        effective_gearing=12.5,
        days_to_expiry=10,
        spread_pct=0.15,
        delta=0.45,
    )
    flags = [
        FlagItem(
            code="SHORT_EXPIRY",
            severity="warn",
            threshold="< 14 days",
            value="10 days",
            text="Approaching expiry in 10 days",
        ),
        FlagItem(
            code="WIDE_SPREAD",
            severity="warn",
            threshold="> 10.0%",
            value="15.0%",
            text="Wide spread of 15%",
        ),
        FlagItem(
            code="HIGH_DECAY",
            severity="high",
            threshold="> 2.0%/day",
            value="3.0%/day",
            text="Steep decay of 3%/day",
        ),
    ]
    card = WarrantCard(
        code="532641",
        issuer="CGS",
        type="Call",
        underlying_ticker="MYEG",
        expiry_date="2026-11-15",
        strike=1.00,
        display_strike="RM 1.00",
        ratio_raw=2.0,
        display_ratio="2:1",
        underlying_price=1.10,
        metrics=metrics,
        flags=flags,
        mode="live",
    )

    desc = build_chat_descriptor(card, mode="live", user_query="What is the gearing and decay?")
    assert desc.code == "532641"
    assert desc.ticker == "MYEG"
    assert desc.option_type == "Call"
    assert len(desc.phrases) >= 3

    # Check each phrase in descriptor
    for phrase in desc.phrases:
        res = verify_no_numbers(phrase)
        assert res.passed, f"Descriptor phrase contained numbers: {phrase} -> {res.offending_tokens}"

    # Check mode phrase
    res_mode = verify_no_numbers(desc.mode_phrase)
    assert res_mode.passed

    # Check glossary items
    assert len(desc.glossary) >= 1
    for item in desc.glossary:
        res_item = verify_no_numbers(item)
        assert res_item.passed


def test_view_link_builders_and_labels():
    """ViewLink builders generate valid in-app or external URLs and digit-free labels."""
    card_link = build_card_link("532641", days=5)
    assert card_link.kind == "card"
    assert card_link.href == "/?tab=card&code=532641&days=5"
    assert card_link.entity == {"code": "532641"}
    assert verify_no_numbers(card_link.label).passed

    scenario_link = build_scenario_link("532641")
    assert scenario_link.kind == "scenario"
    assert scenario_link.href == "/?tab=scenario&code=532641"
    assert verify_no_numbers(scenario_link.label).passed

    compare_link = build_compare_link(["1155A1", "1155B1"])
    assert compare_link.kind == "compare"
    assert compare_link.href == "/?tab=compare&codes=1155A1,1155B1"
    assert compare_link.entity == {"codes": ["1155A1", "1155B1"]}
    assert verify_no_numbers(compare_link.label).passed

    stock_link = build_stock_link("MAYBANK")
    assert stock_link.kind == "stock"
    assert stock_link.href == "/?tab=stock&ticker=MAYBANK"
    assert stock_link.entity == {"ticker": "MAYBANK"}
    assert verify_no_numbers(stock_link.label).passed

    sources_link = build_sources_link(code="532641")
    assert sources_link.kind == "sources"
    assert sources_link.href == "/?tab=sources&code=532641"
    assert verify_no_numbers(sources_link.label).passed

    health_link = build_health_link()
    assert health_link.kind == "health"
    assert health_link.href == "/?tab=health"
    assert verify_no_numbers(health_link.label).passed

    news_link = build_news_link(
        url="https://theedgemalaysia.com/article/maybank",
        ticker="MAYBANK",
        retrieved_at="2026-10-27T10:00:00Z",
    )
    assert news_link.kind == "news"
    assert news_link.href.startswith("https://")
    assert news_link.retrieved_at == "2026-10-27T10:00:00Z"
    assert verify_no_numbers(news_link.label).passed


def test_plain_fallback_templates():
    """Fallback templates must produce digit-free text when given code/ticker allowed tokens."""
    warrant_tmpl = get_plain_warrant_template(
        code="532641",
        ticker="MYEG",
        option_type="Call",
        phrases=["Moderate gearing exposure relative to the underlying share."],
        mode_phrase="Data is sourced from the live exchange market feed.",
    )
    res_w = verify_no_numbers(warrant_tmpl, allowed_tokens=["532641", "MYEG"])
    assert res_w.passed, f"Warrant fallback template failed: {res_w.offending_tokens}"

    term_tmpl = get_plain_term_template(
        term="gearing",
        explanation=get_glossary_term("gearing") or "",
    )
    res_t = verify_no_numbers(term_tmpl)
    assert res_t.passed, f"Term fallback template failed: {res_t.offending_tokens}"

    unknown_tmpl = get_plain_unknown_entity_template("unknown warrant")
    res_u = verify_no_numbers(unknown_tmpl)
    assert res_u.passed, f"Unknown entity fallback template failed: {res_u.offending_tokens}"

    budget_tmpl = get_plain_budget_notice("en")
    res_b = verify_no_numbers(budget_tmpl)
    assert res_b.passed, f"Budget fallback template failed: {res_b.offending_tokens}"

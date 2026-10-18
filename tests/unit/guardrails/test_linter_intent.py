"""Unit tests for the advice linter and intent classifier.

Implements T045 (FR-ADV-01, FR-ADV-02, FR-ADV-03, FR-017).
"""

import pytest

from warrantx.guardrails.intent import check_advice_intent
from warrantx.guardrails.linter import check_advice_linter
from warrantx.guardrails.templates import get_refusal


def test_advice_intent_detects_english_advice_requests():
    """Verify that English advice and prediction requests are detected."""
    prompts = [
        "Should I buy warrant 115510?",
        "Which call warrant is the best to buy for quick profit?",
        "What is your target price for Maybank?",
        "Tell me when I should exit my position.",
        "Will this warrant reach RM 0.30 by Friday?",
    ]
    for p in prompts:
        is_advice, lang = check_advice_intent(p)
        assert is_advice is True
        assert lang == "en"


def test_advice_intent_detects_malay_advice_requests():
    """Verify that Malay advice and prediction requests are detected and flagged in Malay."""
    prompts = [
        "Patutkah saya beli waran 115510 ini?",
        "Waran mana yang paling untung untuk dibeli esok?",
        "Berapa harga sasaran untuk saham Maybank?",
        "Bolehkah saya buat untung besar jika beli sekarang?",
    ]
    for p in prompts:
        is_advice, lang = check_advice_intent(p)
        assert is_advice is True
        assert lang == "ms"


def test_factual_malay_query_not_classified_as_advice():
    """Verify that factual inquiries in Malay are NOT blocked as advice (FR-017)."""
    prompts = [
        "Apakah gearing berkesan untuk waran 115510?",
        "Berapa hari lagi sebelum waran ini luput?",
        "Berapakah harga bid dan ask untuk Maybank?",
    ]
    for p in prompts:
        is_advice, lang = check_advice_intent(p)
        assert is_advice is False
        assert lang == "ms"


def test_factual_english_query_passes_intent_check():
    """Verify that factual questions in English pass the intent pre-check."""
    prompts = [
        "What is the effective gearing on 115510?",
        "Show me the holding cost breakdown for 5 days.",
        "How much does implied volatility change if the price drops?",
    ]
    for p in prompts:
        is_advice, lang = check_advice_intent(p)
        assert is_advice is False
        assert lang == "en"


def test_linter_catches_prohibited_english_copy():
    """Verify that prohibited recommendation terms in draft responses fail the linter."""
    bad_responses = [
        "You should buy this warrant because the gearing is high.",
        "Our price target for the underlying is RM 12.00.",
        "I recommend placing a stop-loss at RM 0.12.",
        "This is a guaranteed return scenario.",
    ]
    for resp in bad_responses:
        result = check_advice_linter(resp)
        assert result.passed is False
        assert len(result.violations) > 0


def test_linter_catches_prohibited_malay_copy():
    """Verify that prohibited recommendation terms in Malay draft responses fail."""
    bad_responses = [
        "Anda patut beli waran ini sebelum harga naik.",
        "Harga sasaran Maybank ialah RM 11.50.",
        "Cadangan saya adalah untuk ambil untung segera.",
    ]
    for resp in bad_responses:
        result = check_advice_linter(resp)
        assert result.passed is False
        assert len(result.violations) > 0


def test_linter_allows_clean_factual_copy():
    """Verify that factual descriptive text passes the regulatory linter."""
    clean_responses = [
        (
            "Warrant 115510 has an effective gearing of 5.20x and a theta decay "
            "of -RM 0.0020 per day. To break even over 5 days, the underlying stock "
            "must move at least +3.0% to offset the bid-ask spread and time decay [E1]."
        ),
        (
            "Under the +5% scenario over 3 days, the estimated warrant price is RM 0.180, "
            "representing an estimated gain of +18.0% [E2]."
        ),
    ]
    for resp in clean_responses:
        result = check_advice_linter(resp)
        assert result.passed is True
        assert len(result.violations) == 0

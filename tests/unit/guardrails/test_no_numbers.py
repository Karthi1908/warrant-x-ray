"""Tests for verify_no_numbers (spec 002, FR-LC-03)."""

import pytest

from warrantx.guardrails.verifier import verify_no_numbers


@pytest.mark.parametrize(
    "text",
    [
        "The gap between the buying and selling price is wide.",
        "This call is far out of the money and may expire worthless.",
        "Open the X-Ray card to see the figures.",
        "Warrant 532641 on 99SMART is risky.",  # identifiers allowed when passed as allowed tokens
    ],
)
def test_clean_text_passes(text):
    res = verify_no_numbers(text, allowed_tokens=["532641", "99SMART"])
    assert res.passed, res.offending_tokens


@pytest.mark.parametrize(
    "text, expected_fragment",
    [
        ("The spread is 40.0% wide.", "40.0%"),
        ("It costs RM 0.015 to enter.", "RM 0.015"),
        ("You need a 33 point move.", "33"),
        ("Gearing is 9.25x here.", "9.25x"),
        ("It could lose half its value.", "half"),
        ("There are two risks to consider.", "two"),
        ("A one hundred percent loss is possible.", "hundred"),
        ("The ratio is 1/4.", "1"),
    ],
)
def test_numbers_are_rejected(text, expected_fragment):
    res = verify_no_numbers(text)
    assert not res.passed
    assert any(expected_fragment in tok for tok in res.offending_tokens), res.offending_tokens


def test_user_typed_numbers_are_allowed():
    res = verify_no_numbers("You asked about a 10% move.", allowed_tokens=["10%"])
    assert res.passed


def test_unlisted_code_is_rejected():
    res = verify_no_numbers("Warrant 532641 is risky.", allowed_tokens=[])
    assert not res.passed


def test_unicode_digits_and_spaced_numbers_rejected():
    assert not verify_no_numbers("Spread is 4\u202f0 percent.").passed

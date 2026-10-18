"""Unit tests for the verify-before-stream grounding verifier and strip_and_note.

Implements T044 (FR-GRD-01, FR-GRD-02, FR-GRD-03).
"""

import pytest

from warrantx.guardrails.templates import get_omission_note
from warrantx.guardrails.verifier import GroundingResult, strip_and_note, verify_grounding


def test_grounding_exact_match():
    """Verify that exact matches against evidence allowlist pass verification."""
    allowlist = {
        "RM 0.150",
        "RM 0.155",
        "42.5%",
        "5.20x",
        "RM 10.20",
        "115510",
        "MAYBANK",
        "E1",
    }
    numeric_values = [0.15, 0.155, 42.5, 5.2, 10.2]

    text = "Warrant 115510 on MAYBANK has a bid of RM 0.150 and ask of RM 0.155 [E1]. The IV is 42.5%."
    result = verify_grounding(text, allowlist=allowlist, numeric_values=numeric_values)
    assert result.is_grounded is True
    assert len(result.ungrounded_tokens) == 0


def test_grounding_detects_hallucinated_number():
    """Verify that an invented number not in the allowlist fails verification."""
    allowlist = {"RM 0.150", "RM 0.155", "42.5%", "E1"}
    numeric_values = [0.15, 0.155, 42.5]

    text = "Warrant 115510 has an IV of 88.5% with delta 0.85 [E1]."
    result = verify_grounding(text, allowlist=allowlist, numeric_values=numeric_values)
    assert result.is_grounded is False
    assert any("88.5" in tok for tok in result.ungrounded_tokens)


def test_grounding_rounding_tolerance():
    """Verify that numbers rounded within standard precision pass rounding check."""
    allowlist = {"5.184x", "42.52%"}
    numeric_values = [5.184, 42.52]

    # Model rounded 42.52% to 42.5% and 5.184x to 5.2x
    text = "The effective gearing is approximately 5.2x with an IV around 42.5%."
    result = verify_grounding(text, allowlist=allowlist, numeric_values=numeric_values)
    assert result.is_grounded is True


def test_grounding_user_typed_numbers():
    """Verify that numbers typed by the user in the prompt are valid in the response."""
    allowlist = {"RM 0.150", "E1"}
    numeric_values = [0.15]
    user_numbers = {"+5%", "3 days", "5", "3"}
    user_numerics = [5.0, 3.0]

    text = "If MAYBANK rises +5% over 3 days, the warrant moves from RM 0.150 [E1]."
    result = verify_grounding(
        text,
        allowlist=allowlist | user_numbers,
        numeric_values=numeric_values + user_numerics,
    )
    assert result.is_grounded is True


def test_grounding_evidence_ids_and_dates():
    """Verify evidence IDs like [E1], [E2] and standard dates pass without error."""
    allowlist = {"2026-06-30", "E1", "E2"}
    numeric_values = []

    text = "The warrant expires on 2026-06-30 according to [E1] and [E2]."
    result = verify_grounding(text, allowlist=allowlist, numeric_values=numeric_values)
    assert result.is_grounded is True


def test_strip_and_note_removes_ungrounded_sentence():
    """Verify that strip_and_note strips the ungrounded sentence and appends omission note."""
    allowlist = {"115510", "RM 0.150", "E1"}
    numeric_values = [0.15]

    text = (
        "Warrant 115510 has a bid of RM 0.150 [E1]. "
        "The expected return is 350% based on secret projections."
    )
    res = verify_grounding(text, allowlist=allowlist, numeric_values=numeric_values)
    assert res.is_grounded is False

    sanitized = strip_and_note(text, ungrounded_tokens=res.ungrounded_tokens, lang="en")
    assert "RM 0.150" in sanitized
    assert "350%" not in sanitized
    assert get_omission_note("en") in sanitized


def test_strip_and_note_noop_when_grounded():
    """Verify that strip_and_note is a no-op when all numbers are verified."""
    allowlist = {"RM 0.150", "E1"}
    numeric_values = [0.15]
    text = "Warrant 115510 has a bid of RM 0.150 [E1]."

    sanitized = strip_and_note(text, ungrounded_tokens=[], lang="en")
    assert sanitized == text

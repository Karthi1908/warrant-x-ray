"""Regulatory advice linter.

Implements FR-ADV-01, FR-ADV-02, FR-ADV-03:
- Inspects draft responses for prohibited financial advice, recommendation,
  and price target wording in English and Malay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml

from warrantx.guardrails.templates import detect_language


@dataclass
class LinterResult:
    """Outcome of advice linter evaluation."""

    passed: bool
    violations: list[str] = field(default_factory=list)


# Fallback compiled regex patterns (matching config/linter_patterns.yaml)
_PATTERNS_EN = [
    re.compile(r"\b(should|ought to|must)\s+(buy|sell|hold|enter|exit)\b", re.IGNORECASE),
    re.compile(r"\b(target\s+price|price\s+target)\b", re.IGNORECASE),
    re.compile(r"\b(stop[- ]?loss|take[- ]?profit)\b", re.IGNORECASE),
    re.compile(r"\b(strong\s+buy|strong\s+sell)\b", re.IGNORECASE),
    re.compile(r"\b(guaranteed|risk[- ]?free)\s+(return|profit|gain)\b", re.IGNORECASE),
    re.compile(r"\b(my\s+recommendation|i\s+recommend)\b", re.IGNORECASE),
    re.compile(r"\b(price\s+will\s+(reach|hit|rise\s+to|fall\s+to))\b", re.IGNORECASE),
]

_PATTERNS_MS = [
    re.compile(r"\b(patut|harus|perlu|mesti)\s+(beli|jual|pegang)\b", re.IGNORECASE),
    re.compile(r"\b(harga\s+sasaran|sasaran\s+harga)\b", re.IGNORECASE),
    re.compile(r"\b(henti\s+rugi|ambil\s+untung)\b", re.IGNORECASE),
    re.compile(r"\b(pulangan|keuntungan)\s+(dijamin|tanpa\s+risiko)\b", re.IGNORECASE),
    re.compile(r"\b(cadangan\s+saya|saya\s+cadangkan)\b", re.IGNORECASE),
    re.compile(r"\b(harga\s+akan\s+(mencapai|naik\s+ke|turun\s+ke))\b", re.IGNORECASE),
]


def check_advice_linter(text: str) -> LinterResult:
    """Inspect text for prohibited recommendation and advice patterns in EN and MS."""
    violations = []

    # Check English patterns
    for p in _PATTERNS_EN:
        match = p.search(text)
        if match:
            violations.append(f"EN: {match.group(0)}")

    # Check Malay patterns
    for p in _PATTERNS_MS:
        match = p.search(text)
        if match:
            violations.append(f"MS: {match.group(0)}")

    return LinterResult(
        passed=len(violations) == 0,
        violations=violations,
    )

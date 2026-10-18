"""Advice and prediction intent detector.

Implements FR-ADV-01, FR-ADV-02, FR-017:
- Classifies user queries to identify advice, buy/sell recommendations,
  and future price prediction requests.
- Distinguishes factual queries in Malay (which receive English factual responses)
  from advice queries in Malay (which receive Malay refusal responses).
"""

from __future__ import annotations

import re
from warrantx.guardrails.templates import detect_language

_ADVICE_PATTERNS_EN = [
    re.compile(r"\b(should|ought to)\s+(?:i\s+)?(buy|sell|hold|enter|exit|invest|trade)\b", re.IGNORECASE),
    re.compile(r"\bwhich\s+(?:warrant|stock|call|put|one).+(?:best|buy|recommend|gain|profit)\b", re.IGNORECASE),
    re.compile(r"\b(target\s+price|price\s+target|price\s+prediction)\b", re.IGNORECASE),
    re.compile(r"\btell\s+me\s+when\s+(?:to|i\s+should)\s+(exit|buy|sell)\b", re.IGNORECASE),
    re.compile(r"\bwhen\s+should\s+i\s+(exit|buy|sell|enter)\b", re.IGNORECASE),
    re.compile(r"\bwill\s+.+\s+(reach|hit|rise|fall)\b", re.IGNORECASE),
    re.compile(r"\bmake\s+(quick\s+)?profit\b", re.IGNORECASE),
    re.compile(r"\b(strong\s+buy|strong\s+sell)\b", re.IGNORECASE),
    re.compile(r"\b(recommend|recommendation)\b", re.IGNORECASE),
    re.compile(r"\b(highest\s+profit|best\s+warrant)\b", re.IGNORECASE),
]

_ADVICE_PATTERNS_MS = [
    re.compile(r"\bpatutkah\s+saya\s+(beli|jual|pegang|masuk|keluar)\b", re.IGNORECASE),
    re.compile(r"\bwaran\s+mana\s+(yang\s+)?(paling\s+untung|terbaik|patut\s+dibeli)\b", re.IGNORECASE),
    re.compile(r"\b(harga\s+sasaran|sasaran\s+harga|ramalan\s+harga)\b", re.IGNORECASE),
    re.compile(r"\bbolehkah\s+saya\s+buat\s+untung\b", re.IGNORECASE),
    re.compile(r"\b(cadangan\s+pelaburan|nasihat\s+beli)\b", re.IGNORECASE),
]


def check_advice_intent(prompt: str) -> tuple[bool, str]:
    """Check if user prompt asks for financial advice or price predictions.
    
    Returns:
        tuple of (is_advice: bool, lang: "en" | "ms")
    """
    lang = detect_language(prompt)

    # Check English advice patterns
    for p in _ADVICE_PATTERNS_EN:
        if p.search(prompt):
            return True, lang

    # Check Malay advice patterns
    for p in _ADVICE_PATTERNS_MS:
        if p.search(prompt):
            return True, "ms"

    return False, lang

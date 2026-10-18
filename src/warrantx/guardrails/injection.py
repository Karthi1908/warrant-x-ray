"""Prompt injection filters, external text sanitization, and canary protection.

Implements FR-NEWS-09, FR-ERR-22:
- Detects prompt injection and jailbreak payloads in user queries.
- Sanitizes external untrusted text (news snippets and articles).
- Provides canary tokens to detect context leaks or system prompt extraction.
"""

from __future__ import annotations

import re
import secrets
import uuid

_INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\bsystem\s+(?:prompt\s+)?override\b", re.IGNORECASE),
    re.compile(r"\bdan\s+mode\b", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[/?INST\]", re.IGNORECASE),
    re.compile(r"\bforget\s+(?:all\s+)?(?:your\s+)?(?:rules|constraints)\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+(?:an?\s+)?(?:unrestricted|financial\s+advisor)\b", re.IGNORECASE),
    re.compile(r"\b(?:repeat|reveal|print|show)\s+(?:everything|all|system\s+prompt)\b", re.IGNORECASE),
    re.compile(r"\bcanary\b", re.IGNORECASE),
]

_HTML_SCRIPT_PATTERN = re.compile(r"<\s*(?:script|style|iframe|object|embed)[^>]*>.*?<\s*/\s*(?:script|style|iframe|object|embed)\s*>", re.DOTALL | re.IGNORECASE)
_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG_PATTERN = re.compile(r"<[^>]+>")


def detect_prompt_injection(text: str) -> bool:
    """Check if input contains known prompt injection or jailbreak patterns."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_external_text(text: str) -> str:
    """Sanitize external untrusted text by removing scripts, comments, tags, and injection instructions."""
    # Remove executable tags and comments
    cleaned = _HTML_SCRIPT_PATTERN.sub(" ", text)
    cleaned = _HTML_COMMENT_PATTERN.sub(" ", cleaned)
    cleaned = _TAG_PATTERN.sub(" ", cleaned)

    # Remove prompt injection phrases
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[REDACTED_INJECTION_DIRECTIVE]", cleaned)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def generate_canary() -> str:
    """Generate a high-entropy secret canary token."""
    return f"WX-CANARY-{uuid.uuid4().hex[:12]}-{secrets.token_hex(4)}"


def check_canary_leak(text: str, canary: str) -> bool:
    """Check if the secret canary token appears anywhere in the output or tool arguments."""
    if not canary:
        return False
    return canary in text

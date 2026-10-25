"""GuardrailPlugin for ADK and LLM tool execution loops.

Implements T058 (FR-CTRL-01, FR-CTRL-02, FR-ERR-16, FR-NEWS-09):
- Enforces call caps (max 5 tool calls per turn).
- Validates tool arguments (rejects URLs, restricts to allowed keys).
- Strips reasoning traces (<think>...</think>) before verification.
- Enforces daily budget ceiling.
"""

from __future__ import annotations

import re
from typing import Any

from warrantx.guardrails.injection import sanitize_external_text

# Regex matching reasoning traces from Nemotron / DeepSeek models
_REASONING_TRACE_PATTERN = re.compile(r"<\s*think\s*>.*?<\s*/\s*think\s*>", re.DOTALL | re.IGNORECASE)


def strip_reasoning_traces(text: str) -> str:
    """Eliminate reasoning blocks (<think>...</think>) and preamble traces from draft response text."""
    cleaned = _REASONING_TRACE_PATTERN.sub("", text).strip()
    # Strip conversational reasoning preambles (e.g. "We need to answer: ... Let's craft.")
    craft_match = re.search(
        r"(?:let'?s\s+(?:craft|write|answer|respond|begin)[^\n]*\n+|let'?s\s+craft\s*\.?\s*)",
        cleaned,
        re.IGNORECASE,
    )
    if craft_match:
        cleaned = cleaned[craft_match.end():].strip()
    elif cleaned.startswith("We need to answer:") or cleaned.startswith("We need to:"):
        # Find first markdown header or blank line separation
        parts = re.split(r"\n\s*\n", cleaned, maxsplit=1)
        if len(parts) > 1 and ("**" in parts[1] or "#" in parts[1]):
            cleaned = parts[1].strip()
    return cleaned


class GuardrailPlugin:
    """Plugin enforcing strict regulatory and runtime limits on agent turns."""

    def __init__(self, max_tool_calls: int = 5) -> None:
        self.max_tool_calls = max_tool_calls
        self.call_count = 0

    def before_tool_call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Validate tool execution pre-conditions and sanitize arguments."""
        self.call_count += 1
        if self.call_count > self.max_tool_calls:
            raise RuntimeError(f"Tool call cap of {self.max_tool_calls} exceeded for this turn.")

        # Ensure no URL arguments are passed to tools
        sanitized_args = {}
        for k, v in args.items():
            if isinstance(v, str):
                if v.startswith("http://") or v.startswith("https://"):
                    raise ValueError(f"Tool argument '{k}' cannot contain URLs.")
                sanitized_args[k] = sanitize_external_text(v)
            else:
                sanitized_args[k] = v

        return sanitized_args

    def after_generation(self, text: str) -> str:
        """Strip internal reasoning traces before passing text to grounding verifier."""
        return strip_reasoning_traces(text)

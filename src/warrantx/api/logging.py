"""Structured logging with request context and strict redaction rules.

Guarantees:
- API keys, bearer tokens, secrets are masked
- Raw IP addresses are masked
- User message text is truncated
- Model reasoning / internal chain-of-thought is never logged
"""

from __future__ import annotations

import logging
import re
import sys
from contextvars import ContextVar
from typing import Any

import structlog

# Context variables for tracing requests across async tasks
request_id_ctx: ContextVar[str | None] = ContextVar("request_id_ctx", default=None)
turn_id_ctx: ContextVar[str | None] = ContextVar("turn_id_ctx", default=None)
session_hash_ctx: ContextVar[str | None] = ContextVar("session_hash_ctx", default=None)

_SENSITIVE_KEYS = {
    "api_key",
    "token",
    "access_token",
    "secret",
    "authorization",
    "password",
    "admin_token",
    "raw_ip",
    "client_ip",
    "remote_addr",
    "reasoning",
    "reasoning_content",
}

_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_KEY_PATTERN = re.compile(r"(?:tvly-[a-zA-Z0-9_-]+|sk-[a-zA-Z0-9_-]+|Bearer\s+[a-zA-Z0-9_\-\.]+)", re.IGNORECASE)


def redact_value(val: Any) -> Any:
    """Redact sensitive patterns in values."""
    if isinstance(val, str):
        val = _KEY_PATTERN.sub("***REDACTED_KEY***", val)
        val = _IP_PATTERN.sub("***REDACTED_IP***", val)
        return val
    elif isinstance(val, dict):
        return {k: ("***REDACTED***" if k.lower() in _SENSITIVE_KEYS else redact_value(v)) for k, v in val.items()}
    elif isinstance(val, list):
        return [redact_value(v) for v in val]
    return val


def redaction_processor(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that strips sensitive information from log records."""
    # 1. Truncate user messages / prompts
    for text_key in ("message", "user_message", "prompt", "query"):
        if text_key in event_dict and isinstance(event_dict[text_key], str):
            text = event_dict[text_key]
            if len(text) > 64:
                event_dict[text_key] = f"{text[:60]}... (len={len(text)})"

    # 2. Drop reasoning content completely
    for reasoning_key in ("reasoning", "reasoning_content", "chain_of_thought", "thinking"):
        if reasoning_key in event_dict:
            event_dict.pop(reasoning_key, None)

    # 3. Mask sensitive keys and patterns
    cleaned: dict[str, Any] = {}
    for k, v in event_dict.items():
        if k.lower() in _SENSITIVE_KEYS:
            cleaned[k] = "***REDACTED***"
        else:
            cleaned[k] = redact_value(v)

    # 4. Inject context variables if not already present
    req_id = request_id_ctx.get()
    if req_id and "request_id" not in cleaned:
        cleaned["request_id"] = req_id

    turn_id = turn_id_ctx.get()
    if turn_id and "turn_id" not in cleaned:
        cleaned["turn_id"] = turn_id

    session_hash = session_hash_ctx.get()
    if session_hash and "session_hash" not in cleaned:
        cleaned["session_hash"] = session_hash

    return cleaned


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """Initialize structured logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redaction_processor,
    ]

    if json_format:
        formatter_processor: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        formatter_processor = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [formatter_processor],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = "warrantx") -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)

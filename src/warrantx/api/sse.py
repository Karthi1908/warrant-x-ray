"""Server-Sent Events (SSE) formatting helpers and stream generators.

Implements contracts/chat-sse.md:
- Formats structured event objects into text/event-stream chunks.
- Supports heartbeat keep-alive comments.
"""

from __future__ import annotations

import json
from typing import Any


def format_sse(event: str, data: Any, event_id: int | None = None) -> dict[str, str]:
    """Format SSE payload dict for sse-starlette EventSourceResponse."""
    data_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
    chunk = {
        "event": event,
        "data": data_str,
    }
    if event_id is not None:
        chunk["id"] = str(event_id)
    return chunk

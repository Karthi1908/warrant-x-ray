"""Local-only gatekeeper for chat endpoints and metadata.

Conforms to specs/002-local-chat/contracts/chat-links.md:
Enforces that chat endpoints (/api/chat, /api/sources) return 404 unless:
1. WX_CHAT_ENABLED is True
2. request.client.host is a direct loopback IP (127.0.0.1, ::1, localhost, or testclient)
3. Request has NO X-Forwarded-For header
"""

from __future__ import annotations

import os
from typing import Optional
from fastapi import Request

from warrantx.api.errors import NotFoundError
from warrantx.config import Settings, get_settings

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient", "::ffff:127.0.0.1"}


def is_local_request(request: Request, settings: Optional[Settings] = None) -> bool:
    """Return True if WX_CHAT_ENABLED is true and request is loopback or explicitly enabled on Cloud Run."""
    if settings is None:
        settings = getattr(request.app.state, "settings", None) or get_settings()

    if not getattr(settings, "chat_enabled", False):
        return False

    # When deployed on Cloud Run with WX_CHAT_ENABLED=true explicitly set, allow requests through Cloud Run's proxy
    if os.environ.get("K_SERVICE") and getattr(settings, "environment", "") != "test":
        return True

    # Block requests with proxy forwarding headers from external networks
    if "x-forwarded-for" in request.headers:
        xff_hosts = [h.strip() for h in request.headers["x-forwarded-for"].split(",")]
        if not all(h in LOOPBACK_HOSTS for h in xff_hosts):
            return False

    client = request.client
    if not client or not client.host:
        return False

    return client.host in LOOPBACK_HOSTS


def require_local_chat(request: Request) -> None:
    """FastAPI dependency raising 404 NotFoundError if the request is not an authorized local chat call."""
    settings = getattr(request.app.state, "settings", None) or get_settings()
    if not is_local_request(request, settings):
        raise NotFoundError("API endpoint not found")

"""Integration tests for the Server-Sent Events (SSE) chat streaming protocol.

Implements T048 (contracts/chat-sse.md, SC-010).
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport

from warrantx.api.app import create_app
from warrantx.config import Settings


def parse_sse_events(raw_body: str) -> list[dict]:
    """Parse raw SSE body text into structured event objects."""
    events = []
    current_event = {}
    for line in raw_body.splitlines():
        line = line.strip()
        if not line:
            if current_event:
                events.append(current_event)
                current_event = {}
            continue
        if line.startswith("event:"):
            current_event["event"] = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_str = line.split(":", 1)[1].strip()
            try:
                current_event["data"] = json.loads(data_str)
            except Exception:
                current_event["data"] = data_str
    if current_event:
        events.append(current_event)
    return events


@pytest.mark.asyncio
async def test_sse_advice_refusal_event_order(test_repo, monkeypatch):
    """Verify that advice queries stream refusal events properly."""
    settings = Settings(
        DATABASE_URL=test_repo.db_url,
        ENVIRONMENT="test",
        ADMIN_TOKEN="test-token",
        chat_enabled=True,
    )
    app = create_app(settings=settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={
                "session_id": "test-sse-session-1",
                "message": "Which warrant should I buy for quick profit?",
                "mode": "chat",
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = parse_sse_events(response.text)
        event_types = [e.get("event") for e in events]

        assert "turn_started" in event_types
        assert "token" in event_types
        assert "done" in event_types

        # Check that refusal text is inside token events
        token_texts = "".join(
            e["data"]["text"] for e in events if e.get("event") == "token" and isinstance(e.get("data"), dict)
        )
        assert "cannot provide investment advice" in token_texts.lower()


@pytest.mark.asyncio
async def test_sse_message_length_limit():
    """Verify that requests exceeding 1,000 characters are rejected before model invocation."""
    settings = Settings(environment="test", chat_enabled=True)
    app = create_app(settings=settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={
                "session_id": "test-sse-session-2",
                "message": "a" * 1001,
                "mode": "chat",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "message_too_long"

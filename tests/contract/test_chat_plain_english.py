"""Contract tests verifying the plain-English SSE stream structure and zero-digits mandate (T019).

Conforms to specs/002-local-chat/contracts/chat-links.md:
- Event order: turn_started -> status* -> evidence* -> token* -> verifier -> links -> done
- No `card` event emitted
- Concatenated token text contains zero digits/numbers (other than user numbers & warrant codes)
"""

import json
import pytest
from httpx import ASGITransport, AsyncClient

from warrantx.api.app import create_app
from warrantx.config import Settings
from warrantx.guardrails.verifier import verify_no_numbers


def parse_sse_events(raw_text: str) -> list[dict]:
    """Parse raw SSE body text into structured event objects."""
    events = []
    current_event = {}
    for line in raw_text.splitlines():
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
async def test_chat_plain_english_event_order_and_zero_digits(test_repo):
    """Verify event sequence, absence of card event, and zero digits in tokens."""
    # Ensure sample database is loaded
    await test_repo.load_synthetic_sample_database()

    settings = Settings(
        DATABASE_URL=test_repo.db_url,
        ENVIRONMENT="test",
        ADMIN_TOKEN="test-token",
        chat_enabled=True,
    )
    app = create_app(settings=settings)
    app.state.repo = test_repo

    transport = ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "session_id": "test-plain-session-1",
                "message": "Explain warrant 115510 and its risks",
                "mode": "sample",
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        events = parse_sse_events(resp.text)
        event_types = [e.get("event") for e in events]

        # 1. Event ordering checks
        assert "turn_started" == event_types[0]
        assert "done" == event_types[-1]
        assert "links" in event_types
        assert "verifier" in event_types

        # Verify links is immediately before done (or after verifier)
        v_idx = event_types.index("verifier")
        l_idx = event_types.index("links")
        d_idx = event_types.index("done")
        assert v_idx < l_idx < d_idx

        # 2. Card event MUST NOT be emitted
        assert "card" not in event_types, "Card event was unexpectedly emitted in plain chat mode"

        # 3. Concatenated token text must have NO numbers except allowed code 115510
        tokens = [
            e["data"]["text"]
            for e in events
            if e.get("event") == "token" and isinstance(e.get("data"), dict) and "text" in e["data"]
        ]
        prose = "".join(tokens)
        check = verify_no_numbers(prose, allowed_tokens=["115510", "MAYBANK"])
        assert check.passed, f"Prose contained forbidden figures: {check.offending_tokens}\nFull text: {prose}"

        # 4. Links event payload contains ViewLink list
        links_event = next(e for e in events if e.get("event") == "links")
        assert "links" in links_event["data"]
        links_list = links_event["data"]["links"]
        assert len(links_list) >= 1
        assert any(link["kind"] == "card" for link in links_list)
        assert any(link["kind"] == "scenario" for link in links_list)


@pytest.mark.asyncio
async def test_chat_term_inquiry_digit_free(test_repo):
    """Glossary term inquiry streams digit-free explanations with exploratory links."""
    await test_repo.load_synthetic_sample_database()

    settings = Settings(
        DATABASE_URL=test_repo.db_url,
        ENVIRONMENT="test",
        ADMIN_TOKEN="test-token",
        chat_enabled=True,
    )
    app = create_app(settings=settings)
    app.state.repo = test_repo

    transport = ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "session_id": "test-term-session-1",
                "message": "What is effective gearing and implied volatility?",
                "mode": "sample",
            },
        )
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        tokens = [
            e["data"]["text"]
            for e in events
            if e.get("event") == "token" and isinstance(e.get("data"), dict) and "text" in e["data"]
        ]
        prose = "".join(tokens)
        check = verify_no_numbers(prose)
        assert check.passed, f"Term explanation contained figures: {check.offending_tokens}"


@pytest.mark.asyncio
async def test_chat_unknown_entity_has_stock_link(test_repo):
    """When an unrecognized entity is asked, reply points to the stock screener without crashing."""
    await test_repo.load_synthetic_sample_database()

    settings = Settings(
        DATABASE_URL=test_repo.db_url,
        ENVIRONMENT="test",
        ADMIN_TOKEN="test-token",
        chat_enabled=True,
    )
    app = create_app(settings=settings)
    app.state.repo = test_repo

    transport = ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "session_id": "test-unknown-sess-1",
                "message": "Tell me about warrant 9999ZZ",
                "mode": "sample",
            },
        )
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        links_event = next(e for e in events if e.get("event") == "links")
        links_list = links_event["data"]["links"]
        assert any(link["kind"] == "stock" for link in links_list)

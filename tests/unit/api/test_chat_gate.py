"""Unit tests for local-only chat gatekeeper matrix (T013).

Covers:
- flag off -> 404
- flag on + non-loopback host -> 404
- flag on + X-Forwarded-For header -> 404
- flag on + loopback -> passes gate
- applies to both /api/chat and /api/sources
- /api/meta reflects chat_enabled accurately
"""

import pytest
from httpx import ASGITransport, AsyncClient

from warrantx.api.app import create_app
from warrantx.config import Settings


@pytest.mark.asyncio
async def test_chat_gate_flag_off_returns_404():
    """When chat_enabled is False, both chat and sources return 404 on loopback."""
    settings = Settings(
        environment="test",
        chat_enabled=False,
    )
    app = create_app(settings=settings)
    transport = ASGITransport(app=app, client=("127.0.0.1", 50000))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # POST /api/chat
        res_chat = await client.post(
            "/api/chat",
            json={"session_id": "s1", "message": "hello", "mode": "chat"},
        )
        assert res_chat.status_code == 404
        assert res_chat.json()["error"]["code"] == "not_found"

        # GET /api/sources
        res_src = await client.get("/api/sources?turn_id=t1")
        assert res_src.status_code == 404
        assert res_src.json()["error"]["code"] == "not_found"

        # GET /api/meta
        res_meta = await client.get("/api/meta")
        assert res_meta.status_code == 200
        assert res_meta.json()["chat_enabled"] is False


@pytest.mark.asyncio
async def test_chat_gate_flag_on_non_loopback_returns_404():
    """When chat_enabled is True, non-loopback client host returns 404."""
    settings = Settings(
        environment="test",
        chat_enabled=True,
    )
    app = create_app(settings=settings)
    # Remote IP
    transport = ASGITransport(app=app, client=("192.168.1.100", 50000))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_chat = await client.post(
            "/api/chat",
            json={"session_id": "s1", "message": "hello", "mode": "chat"},
        )
        assert res_chat.status_code == 404

        res_src = await client.get("/api/sources?turn_id=t1")
        assert res_src.status_code == 404

        res_meta = await client.get("/api/meta")
        assert res_meta.status_code == 200
        assert res_meta.json()["chat_enabled"] is False


@pytest.mark.asyncio
async def test_chat_gate_flag_on_x_forwarded_for_returns_404():
    """When chat_enabled is True and loopback, X-Forwarded-For proxy header returns 404."""
    settings = Settings(
        environment="test",
        chat_enabled=True,
    )
    app = create_app(settings=settings)
    transport = ASGITransport(app=app, client=("127.0.0.1", 50000))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Forwarded-For": "203.0.113.195"}

        res_chat = await client.post(
            "/api/chat",
            json={"session_id": "s1", "message": "hello", "mode": "chat"},
            headers=headers,
        )
        assert res_chat.status_code == 404

        res_src = await client.get("/api/sources?turn_id=t1", headers=headers)
        assert res_src.status_code == 404

        res_meta = await client.get("/api/meta", headers=headers)
        assert res_meta.status_code == 200
        assert res_meta.json()["chat_enabled"] is False


@pytest.mark.asyncio
async def test_chat_gate_flag_on_loopback_passes():
    """When chat_enabled is True and loopback direct, gate passes."""
    settings = Settings(
        environment="test",
        chat_enabled=True,
    )
    app = create_app(settings=settings)
    transport = ASGITransport(app=app, client=("127.0.0.1", 50000))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/sources should pass gate and return list
        res_src = await client.get("/api/sources?turn_id=nonexistent")
        assert res_src.status_code == 200

        # GET /api/meta reflects chat_enabled True
        res_meta = await client.get("/api/meta")
        assert res_meta.status_code == 200
        assert res_meta.json()["chat_enabled"] is True

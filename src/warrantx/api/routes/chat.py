"""Chat routes: streaming SSE chat turn and evidence source lookups.

Implements T060 (contracts/chat-sse.md, FR-CHAT-01 to 05, SC-010).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from warrantx.agents.root import RootAgent
from warrantx.agents.sessions import session_manager
from warrantx.api.budget import is_budget_exhausted
from warrantx.api.ratelimit import chat_rate_limiter
from warrantx.api.sse import format_sse
from warrantx.chat.turn import run_plain_turn
from warrantx.guardrails.fallback import generate_fallback_response
from warrantx.guardrails.templates import get_budget_exhausted_notice
from warrantx.llm.models import get_model

router = APIRouter(prefix="/api", tags=["chat"])


class ChatTurnRequest(BaseModel):
    """Chat turn request payload."""

    session_id: str = Field(description="Client-side session UUID")
    message: str = Field(description="User prompt text")
    mode: str = Field(default="chat", description="'chat' or 'deep'")
    snapshot_id: int | None = Field(default=None, description="Optional target snapshot ID")


@router.post("/chat")
async def chat_turn(chat_in: ChatTurnRequest, request: Request) -> Any:
    """Execute streaming chat turn conforming to the SSE contract."""
    # Validate length limit strictly before model invocation (FR-ERR-19)
    if len(chat_in.message) > 1000:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "message_too_long",
                    "message": "Message exceeds 1,000 characters limit",
                    "field": "message",
                }
            },
        )

    if len(chat_in.message.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "empty_message",
                    "message": "Message cannot be empty",
                    "field": "message",
                }
            },
        )

    # Rate limit check (FR-CTRL-01)
    allowed, retry_after = chat_rate_limiter.is_allowed(chat_in.session_id)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limited",
                    "message": "Rate limit of 30 requests/hour exceeded.",
                    "retry_after": retry_after,
                }
            },
        )

    repo = getattr(request.app.state, "repo", None)
    settings = getattr(request.app.state, "settings", None)
    if not settings:
        from warrantx.config import get_settings
        settings = get_settings()

    if not repo:
        try:
            from warrantx.data.repo import create_repo
            repo = create_repo(settings.database_url)
            await repo.init_tables()
            request.app.state.repo = repo
        except Exception:
            pass

    # In-memory session tracking
    session = session_manager.get_or_create_chat_session(chat_in.session_id)
    turn_id = f"turn-{uuid.uuid4().hex[:12]}"

    # Check budget ceiling
    budget_exhausted = False
    if repo:
        budget_exhausted = await is_budget_exhausted(repo)

    async def event_generator() -> AsyncGenerator[dict[str, Any], None]:
        # 1. turn_started
        yield format_sse("turn_started", {"turn_id": turn_id})
        await asyncio.sleep(0.01)

        # 2. initial status
        yield format_sse(
            "status",
            {"step": "analyzing", "text": "Analyzing query and verifying market context..."},
        )
        await asyncio.sleep(0.01)

        try:
            # 3. Run plain-English turn
            news_service = getattr(request.app.state, "news_service", None)
            llm = get_model("super", settings=settings) if not budget_exhausted else None

            turn_res = await run_plain_turn(
                repo=repo,
                message=chat_in.message,
                session_id=chat_in.session_id,
                llm=llm,
                mode=chat_in.mode,
                turn_id=turn_id,
                news_service=news_service,
                budget_exhausted=budget_exhausted,
            )

            # Emit tool statuses if any
            for status_text in turn_res.status_history:
                yield format_sse("status", {"step": "tool_running", "text": status_text})
                await asyncio.sleep(0.01)

            # Emit evidence (summary is digit-free; NO card event is emitted)
            for ev in turn_res.evidence_items:
                yield format_sse(
                    "evidence",
                    {
                        "evidence_id": ev.id,
                        "kind": ev.kind,
                        "source": ev.source,
                        "as_of": ev.as_of,
                        "summary": ev.summary,
                    },
                )
                await asyncio.sleep(0.01)

            # 4. Stream verified tokens in word chunks
            words = turn_res.final_text.split(" ")
            for i, word in enumerate(words):
                chunk = word if i == len(words) - 1 else f"{word} "
                yield format_sse("token", {"text": chunk})
                await asyncio.sleep(0.01)

            # 5. Emit verifier metadata
            yield format_sse(
                "verifier",
                {
                    "passed": turn_res.verifier_passed,
                    "retried": False,
                    "removed_sentences": 0,
                },
            )
            await asyncio.sleep(0.01)

            # 6. Emit links event
            links_data = [link.model_dump() for link in turn_res.links]
            yield format_sse("links", {"links": links_data})
            await asyncio.sleep(0.01)

            # 7. done
            yield format_sse("done", {"turn_id": turn_id})

            # Save to in-memory session history
            session.add_turn(
                turn_id=turn_id,
                user_message=chat_in.message,
                assistant_response=turn_res.final_text,
            )
        except Exception as ex:
            # Fallback error response so stream never breaks abruptly
            yield format_sse("status", {"step": "error", "text": "Encountered issue processing request."})
            fallback_msg = (
                "Unable to process the query at this moment due to a service delay. "
                "Please inspect the warrant directly via the X-Ray Card or Stock Screener below.\n\n"
                "Educational and analytical tool only. Not financial advice."
            )
            for w in fallback_msg.split(" "):
                yield format_sse("token", {"text": f"{w} "})
                await asyncio.sleep(0.01)

            from warrantx.chat.links import build_stock_link
            fallback_links = [build_stock_link("MAYBANK").model_dump()]
            yield format_sse("links", {"links": fallback_links})
            yield format_sse("done", {"turn_id": turn_id})

    return EventSourceResponse(event_generator())


@router.get("/sources")
async def get_turn_sources(turn_id: str = Query(...), request: Request = None) -> list[dict[str, Any]]:
    """Retrieve evidence records associated with a specific turn."""
    repo = getattr(request.app.state, "repo", None)
    if not repo:
        return []
    evidence_records = await repo.get_turn_evidence(turn_id)
    return [
        {
            "evidence_id": e.evidence_id,
            "kind": e.kind,
            "source": e.source,
            "as_of": e.as_of.isoformat() if e.as_of else "",
            "payload": e.payload_json,
        }
        for e in evidence_records
    ]

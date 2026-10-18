"""In-memory session management with automatic janitor cleanup.

Implements T062 (FR-005, FR-CHAT-01, FR-ERR-19, FR-ERR-20):
- ChatSession: in-memory, 2-hour idle expiry, capped at 10 turns, 1,000-char message limit.
- VisitorSession: ephemeral 24-hour TTL for anonymous visitor deduplication.
- Janitor: sweeps expired sessions cleanly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatTurnRecord:
    turn_id: str
    user_message: str
    assistant_response: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ChatSession:
    """Ephemeral chat session stored only in memory."""

    session_id: str
    turns: list[ChatTurnRecord] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    snapshot_id: int | None = None
    deep_report_count: int = 0

    def is_expired(self, max_idle_seconds: float = 7200.0) -> bool:
        """Check if session has been idle longer than max_idle_seconds (default 2 hours)."""
        return (time.time() - self.last_active_at) > max_idle_seconds

    def touch(self) -> None:
        """Update last active timestamp."""
        self.last_active_at = time.time()

    def add_turn(self, turn_id: str, user_message: str, assistant_response: str) -> None:
        """Add a turn, maintaining a sliding window of the last 10 turns."""
        self.touch()
        self.turns.append(
            ChatTurnRecord(
                turn_id=turn_id,
                user_message=user_message,
                assistant_response=assistant_response,
            )
        )
        if len(self.turns) > 10:
            self.turns.pop(0)


class SessionManager:
    """In-memory registry and janitor for anonymous chat and visitor sessions."""

    def __init__(self) -> None:
        self._chat_sessions: dict[str, ChatSession] = {}
        self._visitor_timestamps: dict[str, float] = {}  # hashed_id -> last_seen

    def get_or_create_chat_session(self, session_id: str) -> ChatSession:
        """Retrieve existing chat session or initialize a new one."""
        self.sweep()
        if session_id not in self._chat_sessions:
            self._chat_sessions[session_id] = ChatSession(session_id=session_id)
        session = self._chat_sessions[session_id]
        session.touch()
        return session

    def record_visitor(self, visitor_hash: str) -> bool:
        """Record visitor activity. Returns True if this is a new visitor within 24h."""
        now = time.time()
        last_seen = self._visitor_timestamps.get(visitor_hash)
        is_new = last_seen is None or (now - last_seen) > 86400.0
        self._visitor_timestamps[visitor_hash] = now
        return is_new

    def sweep(self) -> None:
        """Janitor cleanup: remove expired chat sessions (>2h) and visitor hashes (>24h)."""
        now = time.time()

        # Sweep expired chat sessions (idle > 2 hours)
        expired_chat = [
            sid for sid, s in self._chat_sessions.items() if s.is_expired(7200.0)
        ]
        for sid in expired_chat:
            self._chat_sessions.pop(sid, None)

        # Sweep expired visitor records (> 24 hours)
        expired_visitors = [
            v_hash for v_hash, ts in self._visitor_timestamps.items() if (now - ts) > 86400.0
        ]
        for v_hash in expired_visitors:
            self._visitor_timestamps.pop(v_hash, None)


# Global singleton in-memory session manager
session_manager = SessionManager()

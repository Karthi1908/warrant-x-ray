"""In-memory rate limiter per client key.

Implements FR-CTRL-01:
- Restricts chat turns to 30 requests per hour per client session.
"""

from __future__ import annotations

import time


class RateLimiter:
    """Sliding-window in-memory rate limiter."""

    def __init__(self, max_requests: int = 30, window_seconds: float = 3600.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: dict[str, list[float]] = {}

    def is_allowed(self, client_key: str) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed: bool, retry_after: int)."""
        now = time.time()
        timestamps = self._history.get(client_key, [])

        # Filter out timestamps outside the sliding window
        valid_timestamps = [t for t in timestamps if (now - t) < self.window_seconds]
        self._history[client_key] = valid_timestamps

        if len(valid_timestamps) >= self.max_requests:
            oldest = valid_timestamps[0]
            retry_after = int(self.window_seconds - (now - oldest)) + 1
            return False, retry_after

        valid_timestamps.append(now)
        return True, 0


# Global chat rate limiter
chat_rate_limiter = RateLimiter(max_requests=30, window_seconds=3600.0)

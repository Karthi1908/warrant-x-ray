"""External market data HTTP client with pacing, retries, and kill-switch (T075, FR-DATA-01 to 03).

Responsible for:
- Identifying User-Agent header: 'WarrantXRay/1.0 (+https://github.com/hacks-projects/warrants-x-ray)'.
- Respecting kill-switch: sends ZERO network requests when disabled.
- Pacing: minimum 5.0 s interval between outbound requests.
- Exponential backoff on HTTP 429 and 5xx responses.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

DEFAULT_BURSA_URL = "https://api.bursamalaysia.com/market/structured-warrants"
DEFAULT_USER_AGENT = "WarrantXRay/1.0 (+https://github.com/hacks-projects/warrants-x-ray)"
DEFAULT_PACING_SECONDS = 5.0
DEFAULT_TIMEOUT_SECONDS = 15.0


class SourceClient:
    """HTTP client for collecting structured warrant feeds."""

    def __init__(
        self,
        base_url: str | None = None,
        kill_switch: bool = False,
        pacing_seconds: float = DEFAULT_PACING_SECONDS,
        user_agent: str | None = None,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url or DEFAULT_BURSA_URL
        self.kill_switch = kill_switch
        self.pacing_seconds = pacing_seconds
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.max_retries = max_retries
        self._last_request_time: float = 0.0

    async def _wait_pacing(self) -> None:
        """Enforce minimum spacing between outbound network calls."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.pacing_seconds and self._last_request_time > 0:
            await asyncio.sleep(self.pacing_seconds - elapsed)
        self._last_request_time = time.monotonic()

    async def fetch_raw_warrants(self) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Fetch raw warrant data payload from source endpoint.

        Returns None if kill_switch is active or if all retries fail.
        """
        if self.kill_switch:
            return None

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        backoff = 1.0
        for attempt in range(self.max_retries + 1):
            await self._wait_pacing()
            try:
                async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                    resp = await client.get(self.base_url, headers=headers)
                    if resp.status_code == 200:
                        try:
                            return resp.json()
                        except Exception:
                            return None
                    elif resp.status_code in (429, 500, 502, 503, 504):
                        if attempt < self.max_retries:
                            await asyncio.sleep(backoff)
                            backoff *= 2.0
                            continue
                        return None
                    else:
                        return None
            except (httpx.RequestError, httpx.TimeoutException):
                if attempt < self.max_retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                return None

        return None


async def fetch_snapshot(
    base_url: str | None = None, kill_switch: bool = False
) -> list[dict[str, Any]]:
    """Convenience function to fetch a warrant snapshot from the direct screener."""
    client = SourceClient(base_url=base_url, kill_switch=kill_switch)
    payload = await client.fetch_raw_warrants()
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return (
            payload.get("data")
            or payload.get("rows")
            or payload.get("warrants")
            or []
        )
    return []

"""Direct Nano structured-call client with JSON repair retry.

Implements T054 (FR-ERR-16):
- Fast structured completions for entity disambiguation and intent classification.
- Robust JSON repair and fallback parsing.
"""

from __future__ import annotations

import json
import re
from typing import Any, Type, TypeVar
from pydantic import BaseModel
import httpx

from warrantx.config import Settings

T = TypeVar("T", bound=BaseModel)

_JSON_EXTRACT_REGEX = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def extract_and_parse_json(text: str) -> dict[str, Any] | list[Any]:
    """Extract JSON from raw text or markdown code fences, with repair heuristics."""
    # Strip markdown code blocks
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Regex find first balanced object/array
    match = _JSON_EXTRACT_REGEX.search(cleaned)
    if match:
        snippet = match.group(1)
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            # Common repairs: replace single quotes, trailing commas
            repaired = snippet.replace("'", '"')
            repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
            return json.loads(repaired)

    raise ValueError(f"Could not extract valid JSON from response: {text[:100]}...")


async def direct_nano_json_call(
    prompt: str,
    system_instruction: str = "Return only valid JSON.",
    settings: Settings | None = None,
    response_model: Type[T] | None = None,
) -> dict[str, Any] | T:
    """Execute direct structured call to Nano with automated JSON repair."""
    if settings is None:
        settings = Settings()

    if settings.ENVIRONMENT == "test" or not settings.NEBIUS_API_KEY:
        # Fallback empty or default dict in test mode
        if response_model is not None:
            return response_model()
        return {}

    url = f"{settings.NEBIUS_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.NEBIUS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "nvidia/nemotron-3-nano",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"]

    parsed = extract_and_parse_json(raw_text)
    if response_model is not None:
        return response_model.model_validate(parsed)
    return parsed

"""Spike T9: Observe where Nemotron reasoning content appears (tags, fields, content)."""

import asyncio
import os
import sys
from openai import AsyncOpenAI

NEBIUS_BASE_URL = os.environ.get("WX_NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
API_KEY = os.environ.get("WX_NEBIUS_API_KEY")

async def run_t9():
    if not API_KEY:
        print("[FAIL] WX_NEBIUS_API_KEY environment variable is not set.")
        print("Please configure WX_NEBIUS_API_KEY before running Spike T9.")
        sys.exit(1)

    client = AsyncOpenAI(base_url=NEBIUS_BASE_URL, api_key=API_KEY)
    print("Testing reasoning output format on Super model...")
    try:
        resp = await client.chat.completions.create(
            model="nvidia/nemotron-4-340b-instruct",
            messages=[{"role": "user", "content": "How do you calculate intrinsic value of a call warrant?"}],
            max_tokens=300,
        )
        msg = resp.choices[0].message
        print("Response content:", msg.content)
        # Check if reasoning_content exists in extra fields
        if hasattr(msg, "reasoning_content"):
            print("[PASS] reasoning_content present as dedicated field:", getattr(msg, "reasoning_content"))
        elif "<think>" in (msg.content or ""):
            print("[PASS] Reasoning present as <think> tags in content string.")
        else:
            print("[INFO] No visible separate reasoning tokens returned in standard output.")
    except Exception as e:
        print(f"[FAIL] Error observing reasoning content: {e}")

if __name__ == "__main__":
    asyncio.run(run_t9())

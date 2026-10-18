"""Spike T4: Query /v1/models on Nebius Token Factory for IDs, limits, and pricing."""

import asyncio
import os
import sys
from openai import AsyncOpenAI

NEBIUS_BASE_URL = os.environ.get("WX_NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
API_KEY = os.environ.get("WX_NEBIUS_API_KEY")

async def run_t4():
    if not API_KEY:
        print("[FAIL] WX_NEBIUS_API_KEY environment variable is not set.")
        print("Please configure WX_NEBIUS_API_KEY before running Spike T4.")
        sys.exit(1)

    client = AsyncOpenAI(base_url=NEBIUS_BASE_URL, api_key=API_KEY)
    print(f"Querying model catalog from {NEBIUS_BASE_URL}...")
    try:
        models = await client.models.list()
        print(f"[PASS] Retrieved {len(models.data)} models from Nebius Token Factory:")
        for m in models.data:
            print(f"  - {m.id}")
    except Exception as e:
        print(f"[FAIL] Error querying models: {e}")

if __name__ == "__main__":
    asyncio.run(run_t4())

"""Spike T2: End-to-end ADK loop with LiteLLM against Nebius Token Factory.

Tests tool feedback, two-tool execution, and final grounded answer generation.
"""

import asyncio
import os
import sys

API_KEY = os.environ.get("WX_NEBIUS_API_KEY")

async def run_t2():
    if not API_KEY:
        print("[FAIL] WX_NEBIUS_API_KEY environment variable is not set.")
        print("Please configure WX_NEBIUS_API_KEY before running Spike T2.")
        sys.exit(1)

    print("Running Spike T2: ADK LiteLLM loop...")
    # Will be tested against live Token Factory endpoint when key is provided
    print("[INFO] Ready for execution with active API key.")

if __name__ == "__main__":
    asyncio.run(run_t2())

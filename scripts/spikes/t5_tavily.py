"""Spike T5: Tavily search checks on Malaysian financial news domains."""

import asyncio
import os
import sys
from tavily import AsyncTavilyClient

API_KEY = os.environ.get("WX_TAVILY_API_KEY")
TARGET_DOMAINS = [
    "bursamalaysia.com",
    "theedgemalaysia.com",
    "thestar.com.my",
    "nst.com.my",
    "malaymail.com",
    "focusmalaysia.com",
]

async def run_t5():
    if not API_KEY:
        print("[FAIL] WX_TAVILY_API_KEY environment variable is not set.")
        print("Please configure WX_TAVILY_API_KEY before running Spike T5.")
        sys.exit(1)

    client = AsyncTavilyClient(api_key=API_KEY)
    print("Testing Tavily search on Malaysian financial news for 'Maybank'...")
    try:
        resp = await client.search(
            query="Malayan Banking Berhad Maybank financial results",
            search_depth="advanced",
            include_domains=TARGET_DOMAINS,
            max_results=5,
        )
        results = resp.get("results", [])
        print(f"[PASS] Retrieved {len(results)} results:")
        for r in results:
            print(f"  - [{r.get('published_date', 'no-date')}] {r.get('title')} ({r.get('url')})")
    except Exception as e:
        print(f"[FAIL] Error testing Tavily search: {e}")

if __name__ == "__main__":
    asyncio.run(run_t5())

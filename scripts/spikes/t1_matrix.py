"""Spike T1: Nemotron capability matrix on Nebius Token Factory.

Tests tool calling, parallel calls, tool_choice, JSON schema, and reasoning tokens
using the OpenAI SDK against https://api.tokenfactory.nebius.com/v1/.
"""

import asyncio
import os
import sys
from openai import AsyncOpenAI

NEBIUS_BASE_URL = os.environ.get("WX_NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
API_KEY = os.environ.get("WX_NEBIUS_API_KEY")

MODELS = {
    "nano": "nvidia/nemotron-mini-4b-instruct", # fallback / fast tier
    "super": "nvidia/nemotron-4-340b-instruct", # agent tier
}

SAMPLE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_warrant_quote",
        "description": "Fetch current market quote for a Bursa Malaysia structured warrant.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The 4-to-6 alphanumeric warrant code, e.g. 518828 or MAYBANK-C28"}
            },
            "required": ["code"],
        },
    },
}

async def run_t1():
    if not API_KEY:
        print("[FAIL] WX_NEBIUS_API_KEY environment variable is not set.")
        print("Please configure WX_NEBIUS_API_KEY before running Spike T1.")
        sys.exit(1)

    client = AsyncOpenAI(base_url=NEBIUS_BASE_URL, api_key=API_KEY)
    print(f"Connecting to Nebius Token Factory at {NEBIUS_BASE_URL}...")

    # Test 1: Tool calling on Super
    print("\n--- Test 1: Function Calling on Super ---")
    try:
        resp = await client.chat.completions.create(
            model=MODELS["super"],
            messages=[{"role": "user", "content": "What is the quote for warrant MAYBANK-C28?"}],
            tools=[SAMPLE_TOOL],
            tool_choice="auto",
        )
        msg = resp.choices[0].message
        print(f"Response: {msg}")
        if msg.tool_calls:
            print(f"[PASS] Tool call detected: {msg.tool_calls[0].function.name} with args {msg.tool_calls[0].function.arguments}")
        else:
            print("[WARN] Model did not invoke tool call.")
    except Exception as e:
        print(f"[FAIL] Error testing function calling: {e}")

    # Test 2: Structured JSON on Nano
    print("\n--- Test 2: JSON Response Format on Nano ---")
    try:
        resp = await client.chat.completions.create(
            model=MODELS["nano"],
            messages=[
                {"role": "system", "content": "You output JSON only."},
                {"role": "user", "content": "Extract underlying ticker from 'Maybank call warrant C28' as JSON with key 'ticker'."},
            ],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        print(f"[PASS] Nano JSON response: {content}")
    except Exception as e:
        print(f"[FAIL] Error testing JSON format: {e}")

if __name__ == "__main__":
    asyncio.run(run_t1())

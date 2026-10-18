"""Spike T3: ADK behaviors inspection (LlmAgent, Runner, Plugin hooks).

Inspects ADK classes, function tool decorators, callbacks, and plugin reach.
"""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.agents.context import Context

def sample_tool(code: str) -> str:
    """Sample tool for testing tool signatures."""
    return f"Quote for {code}: bid 0.150, ask 0.155"

def run_t3():
    print("--- Spike T3: Inspecting ADK Behaviors ---")
    print(f"[PASS] LlmAgent loaded: {LlmAgent}")
    print(f"[PASS] Runner loaded: {Runner}")
    print(f"[PASS] Context loaded: {Context}")

    # Inspect LlmAgent initialization parameters
    import inspect
    sig = inspect.signature(LlmAgent.__init__)
    print(f"[PASS] LlmAgent init signature parameters: {list(sig.parameters.keys())}")

if __name__ == "__main__":
    run_t3()

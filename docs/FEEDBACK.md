# Warrant X-Ray Platform & Framework Feedback

This document tracks developer experience feedback, friction logs, and unexpected behaviors encountered with external platforms (Nebius Token Factory, NVIDIA Nemotron, Google ADK, Tavily).

## Feedback Log

| Date | Component / Platform | Observation / Friction | Mitigation / Action | Status |
|:---|:---|:---|:---|:---:|
| 2026-10-16 | Nebius / Nemotron | Function calling compatibility and reasoning token consumption | Scheduled spike T1 (`t1_matrix.py`) to verify tool call format | Open |
| 2026-10-16 | Google ADK | LiteLLM compatibility with custom OpenAI base URLs | Scheduled spike T2 (`t2_adk_loop.py`) with fallback to custom `BaseLlm` | Open |
| 2026-10-16 | Tavily | Malaysian domain coverage and `published_date` consistency | Scheduled spike T5 (`t5_tavily.py`) to benchmark top financial news domains | Open |

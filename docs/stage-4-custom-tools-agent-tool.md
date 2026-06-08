# Stage 4 — Custom Function Tool + AgentTool Composition

## Goal
Add a funding verification capability. Learn where custom function tools can
and cannot be placed, and use AgentTool to compose agents as callable tools.

## Concepts Introduced
- Custom Python function as ADK tool (docstring-driven schema)
- `AgentTool` — wrapping an Agent as a callable tool for another agent
- Tool composition constraints at the Gemini API level
- Multi-agent orchestration without SequentialAgent

## What Changed
Two errors hit before arriving at the working architecture:

**Error 1 — custom function + built-in tool on same agent:**
Adding `verify_funding` function alongside `google_search` on the researcher:
> "Multiple tools are supported only when they are all search tools."

Same API-level restriction as Stage 3. Gemini cannot mix built-in tools and
function calling in a single request.

**Error 2 — stub tool design:**
Moved `verify_funding` to orchestrator (no built-in tools — no conflict).
But stub returned an instruction string expecting the orchestrator to search.
Orchestrator had no `google_search`, so verification failed silently.
Confidence notes read: "verification required further search that could not
be performed by the current tool."

**Working architecture — dedicated verifier agent:**
- `vendor_researcher`: `google_search` only
- `vendor_verifier`: `google_search` only, verification-specific instruction
- `vendor_orchestrator`: `AgentTool(researcher)` + `AgentTool(verifier)` —
  no built-in tools, no conflict
- `vendor_formatter`: `output_schema=VendorSnapshot`, no tools
- `root_agent`: `SequentialAgent([orchestrator, formatter])`

Each agent with `google_search` runs an isolated API request. Orchestrator
coordinates via function calls only. No API constraint violated.

## How to Run
Start a new session per vendor in `adk web`. Test vendors in order:
Solace, CrewAI, AppOrchid, Quantix Mesh AI.

## Observations

| Vendor | Funding Claim | Verdict | Notes |
|---|---|---|---|
| Solace | $790M continuation vehicle, May 2026 | CONFIRMED | Two independent sources |
| CrewAI | $20M Series B, Apr/May 2026 | CONFIRMED | PitchBook, Burkland, Earl Grey Capital |
| AppOrchid | $7.5M debt round | CONFIRMED outside window | Correctly flagged as Oct 2022 — outside 12 months |
| Quantix Mesh AI | $24M Series C, Feb 2026 | UNVERIFIABLE | Only Tracxn; no corroboration |

Quantix Mesh AI disambiguation still broken — orchestrator returned Quantix
(chemical logistics, founded 1965) instead of flagging ambiguity. This is
not a tool composition problem; it requires deterministic vendor-name-match
validation. Stage 6 Critic.

## Gotchas Hit
- Custom function tools and built-in tools cannot coexist on the same agent —
  Gemini API rejects mixed tool mode requests
- Stub tools that return instruction strings fail silently when the calling
  agent lacks the tools to act on them
- `AgentTool` wrapping is the correct pattern: each wrapped agent runs its
  own isolated API request; the outer orchestrator sees only function calls

## Why This Motivates Stage 5
Orchestrator is now coordinating three agents but passing output via prompt
context only — no structured state. If the researcher output is long, the
verifier call is large, and the formatter receives an unstructured blob.
Stage 5 introduces `output_key` on `SequentialAgent` sub-agents to pass
named state between steps cleanly instead of relying on accumulated context.

## Next Stage
Stage 5 — multi-agent `SequentialAgent` with `output_key` session state.
Researcher, Analyst, and Writer as discrete steps. Each agent writes to a
named state key; the next agent reads from it explicitly rather than from
accumulated conversation context.
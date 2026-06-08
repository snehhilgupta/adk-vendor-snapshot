# Stage 3: Pydantic Schema + Two-Agent Pipeline

## Objective
Enforce structured output via Pydantic schema. Learn the ADK constraint that
blocks combining `output_schema` with built-in tools, and implement the
two-agent workaround.

## What Changed
- Added `VendorSnapshot` Pydantic model with seven fields
- Split single agent into two: `vendor_researcher` (search, no schema) and
  `vendor_formatter` (schema, no tools)
- Wired via `SequentialAgent` as `root_agent`
- Switched from AI Studio free tier to Vertex AI (CBRE GCP project) due to
  20 req/day free tier cap

## The ADK Constraint
Setting `output_schema` forces the model into function-calling mode. Gemini's
API does not allow built-in tools (google_search) and function calling in the
same request. Error observed:

> "Built-in tools ({google_search}) and Function Calling cannot be combined
> in the same request."

This is an API-level restriction, not an ADK bug. Resolution: separate the
search and formatting concerns into two agents.

## Observed Behavior

| Vendor | Schema Valid | Notable |
|---|---|---|
| Solace | Yes | $790M continuation vehicle (May 2026) correctly surfaced |
| CrewAI | Yes | Series A cited as Oct 2024 — outside 12-month window; prompt gap |
| AppOrchid | Yes | $43M round (Jun 2025) and Google Cloud partnership correctly surfaced |
| Quantix Mesh AI | Yes | No single entity found; researcher flagged ambiguity; formatter nulled unverifiable fields |

## Quantix Mesh AI: Stage 2 vs Stage 3
- Stage 2: Confident fabrication — stitched four unrelated companies into one snapshot
- Stage 3: Researcher correctly splits into two entities (Quantix AI, Mesh-AI),
  flags no single match. Formatter preserves uncertainty, nulls unverifiable
  fields. `company_name` echoes input rather than verified canonical name —
  expected behavior given no match found.

## Known Gaps
- `recent_activity` is a single string field — source URLs dropped during
  formatting. Schema design trade-off; not a Stage 3 blocker.
- Session bleed observed in `adk web` — prior session context bleeds into new
  runs. Workaround: start a new session per vendor run.
- 12-month window not strictly enforced — researcher included CrewAI Series A
  (Oct 2024) despite being outside window. Prompt refinement needed.

## Environment Note
Switched to Vertex AI mid-stage due to free tier quota exhaustion (20 req/day,
two-agent pipeline = 2 req/run). Auth via `gcloud auth application-default
login`, quota project `cbre-781040876761`.
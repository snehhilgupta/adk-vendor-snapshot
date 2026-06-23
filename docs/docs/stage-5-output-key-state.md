# Stage 5 — Multi-Agent SequentialAgent with output_key Session State

## Goal
Replace prompt-context handoff between agents with named state slot handoff.
Each agent in the SequentialAgent writes its output to a named session state
key. Downstream agents read from named slots explicitly via {state_key}
references in their instructions.

## Concepts Introduced
- `output_key` parameter on Agent — writes final response to named state slot
- ADK session state — runtime dict shared across agents in same session
- `{state_key}` instruction template substitution at agent invocation time
- Explicit data contract between agents vs implicit context bleed

## What Changed
Two minimal changes to Stage 4 architecture:

1. Added `output_key="orchestrator_summary"` to the orchestrator agent
2. Updated formatter instruction to reference `{orchestrator_summary}` from
   state instead of relying on accumulated conversation context

The researcher and verifier did NOT need output_key — they are wrapped as
AgentTools and return values to the orchestrator directly via function call
returns, not as SequentialAgent steps.

Architecture unchanged at the agent-graph level. Only the data-handoff
mechanism changed: from "formatter reads conversation history" to "formatter
reads orchestrator_summary state slot".

## How to Run
Start a new session per vendor in `adk web`. Test vendors:
Solace, CrewAI, AppOrchid, Quantix Mesh AI.

## Observations

| Vendor | Schema Valid | Funding Verdict | Disambiguation |
|---|---|---|---|
| Solace | Yes | $130M Series C CONFIRMED, $60M Series B CONFIRMED | FAILED — returned Solace Health (digital healthcare advocacy) instead of Solace Corporation (event-driven messaging). Regression from Stage 4. |
| CrewAI | Yes | $18M Oct 2024 CONFIRMED (5 sources); $20M April 2026 UNVERIFIABLE (Tracxn-only) | Correct |
| AppOrchid | Yes | No funding identified in last 12 months | Correct |
| Quantix Mesh AI | Yes | N/A | Correct — clean refusal with explicit reasoning about Quantexa AI and AI quantization false matches |

## Stage 5 Key Finding: Schema-Architecture Interaction

Solace regressed from Stage 4 (correct vendor) to Stage 5 (wrong vendor) in
two consecutive fresh sessions. Root cause is not the output_key mechanism —
it is a schema constraint that was always latent and is now exposed.

In the failed run, the orchestrator's summary explicitly stated:
> "The primary challenge was disambiguating between the two prominent
> companies named 'Solace'. This has been addressed by providing separate
> snapshots for the two most relevant and active vendors."

The orchestrator correctly surfaced ambiguity. The formatter received this
in orchestrator_summary state and had to collapse it to a single
VendorSnapshot because the schema permits only one snapshot. It chose
Solace Health.

This is the same failure mode documented in V4 Finding 1 (entity
disambiguation) and V4 Finding 2 (Critic A design gap). Schema enforcement
without a Critic that does deterministic vendor-name-match cannot prevent
this. Stage 6 Critic is now empirically motivated, not just architecturally
argued.

## Why output_key Exposed This

In Stage 4, the formatter received accumulated conversation context
including the researcher's earlier output and verifier verdicts. Solace
Corporation content was buried in that history; the formatter picked it
out by pattern-matching against funding verification evidence.

In Stage 5, the formatter only sees orchestrator_summary. If the orchestrator
synthesizes both candidates equally, the formatter has no signal to prefer
one over the other. The cleaner state handoff inadvertently surfaced a
constraint that was masked by Stage 4's "more data, less structured" approach.

This is a useful finding: structured handoff is not always better than
unstructured context when the structure doesn't carry enough signal to make
downstream decisions.

## Concrete Evidence output_key Worked

Stage 4 formatter output (Solace):
> confidence_note: "...sources include LeadIQ, Solace's press releases..."

Stage 5 formatter output (Solace):
> confidence_note: "...VERDICT: CONFIRMED: At least two independent sources
> corroborate the claim. Solace Health raised $130 million in Series C
> funding on February 10, 2026..."

Verification verdicts are now present in Stage 5 confidence_note in
structured form. Stage 4 had verdicts buried in orchestrator prose and
sometimes dropped during formatter compression.

## Gotchas Hit
- output_key on agents wrapped as AgentTool has no effect — AgentTool returns
  the agent's output directly to the caller. Only SequentialAgent steps need
  output_key.
- {state_key} substitution happens at agent invocation time, not session
  start. Each Agent gets a freshly-substituted instruction string per turn.
- Solace regression was misdiagnosed as session bleed initially. Two fresh
  sessions returned the same wrong vendor — ruled out session state issue.

## Why This Motivates Stage 6
Stage 5 demonstrated that explicit state handoff exposes — does not solve —
the entity disambiguation gap. A Critic agent that performs deterministic
vendor-name-match against the original input would have caught Solace Health
substitution. Stage 6 builds that Critic.

## Next Stage
Stage 6 — Critic agent with deterministic vendor-name-match. Read
orchestrator_summary state, compare canonical vendor name against original
input, reject substitution explicitly. String-level comparison, not LLM-based
judgment.
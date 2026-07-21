# ADK Vendor Snapshot

A hands-on learning project for Google's Agent Development Kit (ADK). The use case is a Vendor Snapshot generator — input a vendor name, get a structured snapshot covering company basics, product summary, recent activity, and a confidence note.

## Use Case

**Input:** vendor name (e.g. "Solace", "CrewAI")
**Output:** structured JSON snapshot per Pydantic schema

**Test vendors:**
- Solace — real, well-documented
- CrewAI — real, fast-moving
- AppOrchid — real, lower visibility
- Quantix Mesh AI — fabricated, used for disambiguation and hallucination testing

## Environment

- Python 3.14, Windows, VS Code, PowerShell
- ADK 2.1.0
- Gemini 2.5 Flash via Vertex AI (GCP project)
- Git + GitHub

## Study Path

| Stage | Concept | Doc | Status |
|-------|---------|-----|--------|
| 0 | Environment setup, project skeleton, placeholder agent | [stage-0-setup.md](docs/stage-0-setup.md) | ✅ |
| 1 | Single agent, no tools — training data limits | [stage-1-bare-agent.md](docs/stage-1-bare-agent.md) | ✅ |
| 2 | Built-in Google Search grounding | [stage-2-grounded-search.md](docs/stage-2-grounded-search.md) | ✅ |
| 3 | Pydantic schema + two-agent search-formatter pipeline | [stage-3-pydantic-schema.md](docs/stage-3-pydantic-schema.md) | ✅ |
| 4 | Custom function tool + AgentTool composition | [stage-4-custom-tools-agent-tool.md](docs/stage-4-custom-tools-agent-tool.md) | ✅ |
| 5 | Multi-agent SequentialAgent with output_key session state | [stage-5-output-key-state.md](docs/stage-5-output-key-state.md) | ✅ |
| 6 | Critic agent with deterministic vendor-name-match | — | — |
| 7 | LoopAgent with termination-on-Critic-approved + callbacks | — | — |
| 8 | Evaluation with adk eval — test sets, regression on 4 vendors | — | — |
| 9 | Session state + in-process memory (InMemorySessionService) — Google/ADK native | — | — |
| 9.1 | External memory as system-of-record cache — Mem0 OSS | [stage-9-1-mem0-memory-system-of-record.md](docs/stage-9-1-mem0-memory-system-of-record.md) | ✅ |
| 9.2 | AgentCore Memory (short-term DynamoDB + long-term vector) — AWS Bedrock | [stage-9-2-agentcore-memory.md](docs/stage-9-2-agentcore-memory.md) | ✅ |
| 9.3 | Vertex AI Memory Bank (managed) — Google | [stage-9-3-vertex-memory-bank.md](docs/stage-9-3-vertex-memory-bank.md) | ✅ |
| 9.4 | MAF agent harness + Foundry IQ memory — Azure | — | — |
| 10 | Deployment surfaces — architectural read-only | — | — |

## Repository Structure

adk-vendor-snapshot/
├── vendor_snapshot/
│   ├── __init__.py
│   ├── agent.py
│   ├── mem0_store.py
│   ├── pipeline.py
│   ├── vendor_service.py
│   └── .env
├── docs/
│   ├── stage-0-environment.md
│   ├── stage-1-bare-agent.md
│   ├── stage-2-google-search.md
│   ├── stage-3-pydantic-schema.md
│   ├── stage-4-custom-tools-agent-tool.md
│   ├── stage-9-1-mem0-memory-system-of-record.md
│   └── stage-9-3-vertex-memory-bank.md
├── .gitignore
└── README.md

## Key Findings by Stage

**Stage 1 — no tools:** Four failure modes documented: confident-stale (Solace), outdated-mental-model (CrewAI), partial-fabrication (AppOrchid), clean-refusal (Quantix Mesh AI). Clean refusal was the only correct behavior — triggered only because zero training data existed for the fabricated vendor.

**Stage 2 — search grounding:** Recency and specific facts corrected for Solace, CrewAI, AppOrchid. Quantix Mesh AI regressed — grounding gave the model more material to confabulate with, stitching four unrelated companies into one snapshot instead of refusing.

**Stage 3 — Pydantic schema:** `output_schema` forces function-calling mode; Gemini API blocks combining this with built-in tools. Workaround: two-agent pipeline — researcher (search, no schema) → formatter (schema, no tools) via SequentialAgent. Quantix Mesh AI improved — researcher flagged ambiguity, formatter nulled unverifiable fields.

**Stage 4 — AgentTool:** Custom function tools and built-in tools cannot coexist on the same agent — Gemini API rejects mixed tool mode requests. Solution: dedicated verifier agent wrapped as AgentTool. Funding verdicts: Solace $790M CONFIRMED, CrewAI $20M Series B CONFIRMED, AppOrchid $7.5M correctly flagged outside 12-month window, Quantix $24M Series C UNVERIFIABLE. Disambiguation still broken — requires Stage 6 Critic.

**Stage 9.3 — Vertex AI Memory Bank:** Adversarially tested contradiction handling across six tests (soft and sharp claims, managed and custom topics, isolated and non-isolated records). Memory Bank does not supersede on contradiction — it merges the new claim into the existing record as a hedge ("X, though previously noted as Y"), and hedges chain across repeated contradictions without bound. No duplication (unlike Mem0 OSS), but no resolution either. Raising `revisions_per_candidate_count` from 1 to 5 did not change this behavior, ruling out revision-depth as the controlling mechanism. Dashboard-level metrics (record count, update timestamp) look healthy throughout — the degradation is only visible by reading the fact text itself.

## ADK Quirks

- `adk web` does not hot-reload `agent.py` — restart server after every code change
- Built-in `google_search` produces no separate trace node — verify via output content, not trace shape
- `output_schema` and built-in tools cannot coexist on the same agent (API constraint)
- Custom function tools and built-in tools cannot coexist on the same agent (API constraint)
- `AgentTool` wrapping isolates each agent's API request — no constraint violations
- Session bleed in `adk web` — start a new session per vendor run
- `.env` lives inside `vendor_snapshot/`, not the project root
- `vertexai.types` (per current Google docs) is not importable on `google-cloud-aiplatform==1.158.0` — actual path is `vertexai._genai.types`
- Memory Bank custom topics are configured at the instance level via `client.agent_engines.update()`, not per-call — any update replaces the full `customization_configs` block
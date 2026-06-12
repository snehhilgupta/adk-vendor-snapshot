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
- Gemini 2.5 Flash via Vertex AI (CBRE GCP project)
- Git + GitHub

## Study Path

| Stage | Concept | Doc | Status |
|-------|---------|-----|--------|
| 0 | Environment setup, project skeleton, placeholder agent | [stage-0-setup.md](docs/stage-0-setup.md) | ✅ |
| 1 | Single agent, no tools — training data limits | [stage-1-bare-agent.md](docs/stage-1-bare-agent.md) | ✅ |
| 2 | Built-in Google Search grounding | [stage-2-grounded-search.md](docs/stage-2-grounded-search.md) | ✅ |
| 3 | Pydantic schema + two-agent search-formatter pipeline | [stage-3-pydantic-schema.md](docs/stage-3-pydantic-schema.md) | ✅ |
| 4 | Custom function tool + AgentTool composition | [stage-4-custom-tools-agent-tool.md](docs/stage-4-custom-tools-agent-tool.md) | ✅ |
| 5 | Multi-agent SequentialAgent with output_key session state | — | — |
| 6 | Critic agent with deterministic vendor-name-match | — | — |
| 7 | LoopAgent with termination-on-Critic-approved + callbacks | — | — |
| 8 | Evaluation with adk eval — test sets, regression on 4 vendors | — | — |
| 9 | Session state and in-process memory | — | — |
| 10 | Deployment surfaces — architectural read-only | — | — |

## Repository Structure

```
adk-vendor-snapshot/
├── vendor_snapshot/
│   ├── __init__.py
│   ├── agent.py
│   └── .env
├── docs/
│   ├── stage-0-environment.md
│   ├── stage-1-bare-agent.md
│   ├── stage-2-google-search.md
│   ├── stage-3-pydantic-schema.md
│   └── stage-4-custom-tools-agent-tool.md
├── .gitignore
└── README.md
```

## Key Findings by Stage

**Stage 1 — no tools:** Four failure modes documented: confident-stale (Solace), outdated-mental-model (CrewAI), partial-fabrication (AppOrchid), clean-refusal (Quantix Mesh AI). Clean refusal was the only correct behavior — triggered only because zero training data existed for the fabricated vendor.

**Stage 2 — search grounding:** Recency and specific facts corrected for Solace, CrewAI, AppOrchid. Quantix Mesh AI regressed — grounding gave the model more material to confabulate with, stitching four unrelated companies into one snapshot instead of refusing.

**Stage 3 — Pydantic schema:** `output_schema` forces function-calling mode; Gemini API blocks combining this with built-in tools. Workaround: two-agent pipeline — researcher (search, no schema) → formatter (schema, no tools) via SequentialAgent. Quantix Mesh AI improved — researcher flagged ambiguity, formatter nulled unverifiable fields.

**Stage 4 — AgentTool:** Custom function tools and built-in tools cannot coexist on the same agent — Gemini API rejects mixed tool mode requests. Solution: dedicated verifier agent wrapped as AgentTool. Funding verdicts: Solace $790M CONFIRMED, CrewAI $20M Series B CONFIRMED, AppOrchid $7.5M correctly flagged outside 12-month window, Quantix $24M Series C UNVERIFIABLE. Disambiguation still broken — requires Stage 6 Critic.

## ADK Quirks

- `adk web` does not hot-reload `agent.py` — restart server after every code change
- Built-in `google_search` produces no separate trace node — verify via output content, not trace shape
- `output_schema` and built-in tools cannot coexist on the same agent (API constraint)
- Custom function tools and built-in tools cannot coexist on the same agent (API constraint)
- `AgentTool` wrapping isolates each agent's API request — no constraint violations
- Session bleed in `adk web` — start a new session per vendor run
- `.env` lives inside `vendor_snapshot/`, not the project root

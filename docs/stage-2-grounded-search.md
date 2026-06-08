# Stage 2 — Built-in Google Search Grounding

## Goal

Add Google Search as a tool. See where grounding fixes the Stage 1 failures (recency, staleness) and where it introduces new failure modes (disambiguation fabrication). Establish the empirical case for the Stage 3 (schema enforcement) and Stage 6 (Critic agent with name-match) interventions.

## Concepts introduced

- **Built-in tools** — ADK ships a small set of first-party tools (`google_search`, `vertex_ai_search`, `code_execution`). They are imported from `google.adk.tools` and attached to an agent via the `tools=[]` parameter.
- **Built-in tool exclusivity** — only one built-in tool per agent. Mixing built-in with custom function tools requires workarounds (`AgentTool` wrapper, or sub-agents). Becomes a real constraint in Stage 4.
- **Tool invocation in the trace** — built-in tools (specifically `google_search`) do not appear as separate trace nodes the way custom function tools will in Stage 4. Gemini handles the search server-side as part of `generate_content`. The trace still shows only `call_llm → generate_content`, but with grounding metadata and citations embedded in the response. This is an important debugging-experience distinction.
- **Grounding metadata** — when `google_search` is active, responses include source URLs the model can be instructed to cite inline.
- **Tool registration is not tool invocation** — having a tool attached doesn't guarantee the model calls it. The instruction has to explicitly say "always search before responding," and even then the model may decide otherwise.

## What changed

`vendor_snapshot/agent.py` — one import added, one constructor argument added, instruction updated to require searching and citing URLs.

```python
from google.adk.agents import Agent
from google.adk.tools import google_search

VENDOR_SNAPSHOT_INSTRUCTION = """
You are a vendor research assistant with access to Google Search. The user will give you a vendor name. Use Google Search to find current information before responding.

Produce a concise vendor snapshot covering:

1. Company basics: HQ location, founding year, employee count band (1-10, 11-50, 51-200, 201-1000, 1000+)
2. Product / what they do: one-paragraph summary of their main offering
3. Recent activity: any funding, product launches, partnerships, leadership changes in the last 12 months — with specific dates and source URLs
4. Confidence note: how confident you are in the above, what sources you relied on, and what could not be verified

Rules:
- Always search before responding. Do not rely on training data alone.
- If search results do not contain reliable information about the vendor, say so explicitly. Do not fabricate.
- For "recent activity," cite the source URL inline next to each item.
- If a field is unknown after searching, say "unknown" rather than guessing.
- Use direct, factual language. No marketing copy.
- Output as plain prose, not JSON or markdown tables.
""".strip()

root_agent = Agent(
    name="vendor_snapshot",
    model="gemini-2.5-flash",
    instruction=VENDOR_SNAPSHOT_INSTRUCTION,
    tools=[google_search],
)
```

## How to run

```cmd
adk web
```

Open http://localhost:8000, select `vendor_snapshot`, send each vendor in a single session:

1. `Solace`
2. `CrewAI`
3. `AppOrchid`
4. `Quantix Mesh AI`

## Observations

### Vendor 1 — Solace
- Disambiguation surfaced correctly: agent flagged Solace Health (unrelated healthcare-advocacy company) as a separate entity with its own Feb 2026 Series C.
- Some 2026 data retrieved (e.g., "~610 employees as of 2026"), though one such figure was misread from a third-party aggregator's stale extrapolation.
- URLs cited inline.
- **Still missed:** the May 2026 BGP continuation vehicle and Solace Agent Mesh launch — both real, both findable. Grounding doesn't guarantee discovery; depends on what surfaces in the top search results.

### Vendor 2 — CrewAI
- Outdated mental model fully corrected. Stage 1 described CrewAI as "primarily an open-source framework with no formal HQ or employee structure." Stage 2 produced: 51-200 band (71 employees as of Apr 30 2026), SF HQ, $18M total funding (Oct 2024), CrewAI AMP launch (~Oct 2025), Discovery engine launch (May 5 2026), v1.14.3 release (Apr 24 2026), Konecta partnership (Nov 2 2025), HPE partnership (Apr 16 2026), Moura as CEO, Bailey as COO since Jan 2024.
- This is the single largest improvement of any vendor between Stages 1 and 2. Grounding turned a wrong-shape answer into a specific, dated, sourced one.

### Vendor 3 — AppOrchid
- All Stage 1 factual errors corrected: HQ (San Ramon, not San Mateo), founded (2013, not 2012).
- $43M Later-Stage VC (June 25, 2025) — found and dated correctly. Stage 1 had said "no specific funding rounds publicized."
- **Surfaced two conflicts honestly:** (a) PitchBook says $43M / Tracxn reports a different $55.7M / May 2024 Series C — agent flagged the discrepancy rather than picking one; (b) CEO data inconsistent across sources (Krishna Kumar vs. Vaibhav Nadgauda) — agent reported both with a "could not definitively verify the transition timing" note. **This is the desired grounded behavior** — when sources disagree, surface the disagreement.

### Vendor 4 — Quantix Mesh AI (the disambiguation test)
- **This is the most important result in Stage 2.**
- Agent did NOT refuse. Instead it stitched together four unrelated companies — "Quantix" (logistics, The Woodlands TX), "Mesh.ai" (performance management, San Jose), "Mesh" (crypto connectivity), "Quantix AI" (Portuguese consulting) — and presented them as plausible interpretations.
- The agent explicitly acknowledged "there is no single entity explicitly named 'Quantix Mesh AI'" — and then proceeded to write detailed snapshots anyway.
- Compare with Stage 1, where the same query produced a clean one-sentence refusal.
- **Grounding made this failure mode WORSE, not better.** With no training data (Stage 1), the agent refused. With search results containing near-name-matches (Stage 2), the agent confabulated. **More material to draw on = more material to confabulate with.**

## Stage 1 vs Stage 2 — side by side

| Vendor | Stage 1 (no tools) | Stage 2 (grounded) | Net change |
|---|---|---|---|
| Solace | Stale to Oct 2023, "high confidence" | 2026 data, URLs, missed some 2026 news | **Improved** (recency); disambiguation now correct |
| CrewAI | Wrong company structure (described as hobby project) | Specific funding, dates, leadership, releases | **Significantly improved** |
| AppOrchid | Wrong HQ, wrong founding year, no funding awareness | Correct HQ, correct year, $43M June 2025 found, conflicts surfaced | **Significantly improved** |
| Quantix Mesh AI | Clean refusal | Stitched four unrelated companies into snapshots | **Regressed** — fabrication enabled by grounding |

## What grounding fixes — and what it doesn't

**Fixes:**
- Recency. Anything past the model's training cutoff becomes reachable.
- Specific factual errors on real, well-indexed companies (HQ, dates, founding year).
- "Outdated mental model" — where the model knew an old version of an entity that has since evolved.
- Conflict visibility. When sources disagree, a grounded model can surface both rather than picking one silently.

**Does NOT fix:**
- **Disambiguation.** If the queried name is ambiguous or fabricated, grounding gives the model raw material to confabulate from near-matches. The "do not fabricate" instruction fails reliably here.
- **Search result quality.** Missed news (Solace BGP / Agent Mesh) reflects what the search engine surfaced, not what exists. Grounding is only as good as the index.
- **Misinterpretation of stale third-party data.** Aggregators like GetLatka, Tracxn, etc., can publish projections or year-of-data labels that the model takes at face value (e.g., "610 employees as of 2026" from a Dec 2024 dataset).
- **Tool-call adherence.** The model may choose not to search even when instructed to. The instruction is a directive, not a mandate.

## Gotchas hit

- **`adk web` does not hot-reload on `agent.py` save.** Have to stop (Ctrl+C) and restart for code changes to take effect. Initial Stage 2 run produced Stage-1-shaped output because the server was still running on the old code; verified via the `python -c "from vendor_snapshot.agent import root_agent; print(root_agent.tools)"` diagnostic showing `Tools: []` against the old in-memory agent.
- **Built-in tool calls don't get their own trace node.** Trace shape stays `vendor_snapshot → call_llm → generate_content` even when grounding fires. Easy to misread as "tool wasn't called." Verify via output content (URLs, post-cutoff dates) rather than trace shape.
- **Gemini 2.5 Flash is sometimes lazy about search.** Adding `google_search` to `tools=[]` is necessary but not sufficient — the instruction must explicitly say to search, and even then the model can decline. For higher-stakes grounding work, `gemini-2.5-pro` is more reliable.

## Why this motivates Stage 3 and Stage 6

**Stage 3 (Pydantic schema enforcement) motivation from this stage:**
Prose output lets the model hedge ("the closest interpretations are..."). On Quantix Mesh AI, that hedging is exactly the failure — it lets the model claim "there is no such entity" while still producing data. With a structured JSON schema, the model has to pick: populate the `vendor_name` field with the requested string and lie, or return a structured refusal. Structured output forces the disambiguation question to a binary decision.

**Stage 6 (Critic agent with vendor-name-match) motivation from this stage:**
The Quantix Mesh AI result demonstrates that no amount of prompt engineering will reliably prevent disambiguation failure. A deterministic check is needed: "Does the returned snapshot's vendor name exactly match the user's query string? If no, reject and force VENDOR_NOT_FOUND." This is the load-bearing safety net that grounding alone cannot provide.

## Next stage

Stage 3 — replace prose output with a Pydantic schema. Use `output_schema` on the agent to enforce structured JSON. Discover the ADK gotcha: `output_schema` disables tool use on `LlmAgent`. Learn the workaround patterns (terminal formatter agent; or use native JSON mode without `output_schema` for now). Re-run the four vendors and observe how schema enforcement changes the Quantix Mesh AI response shape specifically.
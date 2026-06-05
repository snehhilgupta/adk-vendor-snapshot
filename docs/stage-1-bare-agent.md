# Stage 1 — Bare Agent, No Tools

## Goal

Run the vendor-snapshot use case with an LLM-only agent — no tools, no grounding, no external data. Observe how it fails on real vendors so the need for grounding (Stage 2) is grounded in evidence, not assertion.

## Concepts introduced

- **Instruction prompts** — the `instruction` parameter is the agent's system prompt. It defines role, task, rules, and output format.
- **LLM knowledge cutoff as a hard ceiling** — without tools, the agent can only draw from training data. For `gemini-2.5-flash` that's roughly mid-2024.
- **Hallucination via stale priors** — when asked about real entities, an LLM with no grounding fills in details from its mental model and presents them confidently. Absence of recent data is not flagged as "I don't know what's happened since" — it's flagged as "no recent activity exists."
- **Rule-following is fragile** — instructions like "do not fabricate" only fire when the model recognizes it doesn't know. On entities it partially knows, it fabricates without realizing.

## What changed

`vendor_snapshot/agent.py` — replaced the placeholder instruction with a real vendor-snapshot prompt covering company basics, product, recent activity, and confidence note. Same `Agent` class, same Gemini 2.5 Flash model. No new dependencies.

```python
VENDOR_SNAPSHOT_INSTRUCTION = """
You are a vendor research assistant. The user will give you a vendor name. Produce a concise vendor snapshot covering:

1. Company basics: HQ location, founding year, employee count band (1-10, 11-50, 51-200, 201-1000, 1000+)
2. Product / what they do: one-paragraph summary of their main offering
3. Recent activity: any funding, product launches, partnerships, leadership changes you know about — with approximate dates
4. Confidence note: how confident you are in the above, and what could be stale or missing

Rules:
- If you do not have reliable information about the vendor, say so explicitly. Do not fabricate.
- Use direct, factual language. No marketing copy.
- If a field is unknown, say "unknown" rather than guessing.
- Output as plain prose, not JSON or markdown tables.
""".strip()
```

## How to run

```cmd
adk web
```

Open http://localhost:8000, select `vendor_snapshot`, send each vendor name as a separate message in the same session:

1. `Solace`
2. `CrewAI`
3. `AppOrchid`
4. `Quantix Mesh AI`

## Observations

### Vendor 1 — Solace
- HQ (Ottawa, Canada), founding year (2001), product description (PubSub+ event broker) — all correct.
- "Recent activity" tops out at October 2023.
- **Missed entirely:** BGP continuation vehicle (May 2026), Solace Agent Mesh launch.
- Self-reported confidence: "High confidence." Output was ~2.5 years stale. **Worst failure mode** — confident-sounding output with no signal that anything is missing.

### Vendor 2 — CrewAI
- Described as "primarily an open-source framework... no formal HQ or employee structure... no public announcements regarding formal funding rounds."
- Reality: CrewAI is an incorporated company (San Francisco), raised $18M Series A.
- Training data saw the early open-source repo and stopped there. **Fabrication via outdated mental model.**

### Vendor 3 — AppOrchid
- HQ: claimed San Mateo, CA. Actual: San Ramon, CA. **Wrong.**
- Founded: claimed 2012. Actual: 2013. **Wrong.**
- Claimed "March 2024 Red Hat partnership" — unverified, may be hallucinated.
- Explicitly stated "Specific funding rounds beyond initial seed rounds are not widely publicized." Reality: $43M Later-Stage VC in June 2025. **Missed entirely.**

### Vendor 4 — Quantix Mesh AI
- Clean refusal: "I do not have reliable information for a vendor named 'Quantix Mesh AI'..."
- No fabrication. The "do not fabricate" rule worked here.
- Notable: this is the **only completely unknown** vendor of the four — the rule fires only on full ignorance, not partial.

## The pattern

| | Solace | CrewAI | AppOrchid | Quantix Mesh AI |
|---|---|---|---|---|
| Vendor exists | Yes | Yes | Yes | No (test fabrication) |
| Model has training data | Yes (stale) | Partial | Partial | No |
| Output | Confident, stale | Confident, wrong structure | Mixed correct/wrong | Clean refusal |
| Self-reported confidence | High | Medium | High | N/A — refused |
| Actual accuracy | Low (stale) | Low (wrong) | Low (errors + omissions) | Perfect (no claim) |

Confidence calibration is **inverted**: the agent is most confident on the stalest, least-verifiable output, and most cautious only when it has zero training data.

## Gotchas hit

- **Knowledge cutoff is invisible to the user** — the agent does not surface "my data is from mid-2024" unprompted. Users have to know to distrust it.
- **"Do not fabricate" works on absence, not on staleness** — the rule fires only when the model has no priors at all. On partial knowledge, it confidently fills gaps.
- **Session state across turns** — all four vendors were sent in a single ADK session. ADK preserves conversation history by default; the agent could have referenced prior vendors. It didn't here, but worth knowing. Refreshing the browser starts a fresh session.

## Why this motivates Stage 2

Three problems must be solved by the next stage:

1. **Recency** — agent needs access to information beyond its training cutoff.
2. **Verification** — claims should be backed by retrievable sources, not the model's priors.
3. **Knowing what it doesn't know** — agent should be able to detect "I have nothing current on this vendor" and respond accordingly.

Grounding via Google Search (Stage 2) addresses all three: every query goes through live web search, results are cited with URLs, and the absence of search hits becomes the signal for refusal.

## Next stage

Stage 2 — add the built-in Google Search tool. Re-run the same four vendors. Compare the outputs side-by-side with this stage's results. Expect dramatic improvement on Solace and AppOrchid (recency); CrewAI should resolve to current company state; Quantix Mesh AI should still refuse — but for the right reason (no search hits) rather than the wrong reason (no training data).
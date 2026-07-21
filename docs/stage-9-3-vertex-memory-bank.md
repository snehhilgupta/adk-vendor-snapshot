# Stage 9.3 — Vertex AI Memory Bank (Managed, Google)

## Evidence basis

Mixed. Architecture, integration model, and API shape are [vendor-docs] (Google Cloud documentation, verified via web search/fetch against installed SDK version — not assumed from training data). All consolidation/supersession findings are [observed] — hands-on, adversarially tested, not a guided workshop. This stage is the most adversarially tested of the 9.x track to date.

## Goal

Understand Vertex AI Memory Bank's architecture and, hands-on, its consolidation/supersession behavior on contradiction — the sharpest cross-platform axis identified across 9.1 (Mem0) and 9.2 (AgentCore). Specifically: does Memory Bank genuinely supersede contradicted facts, or accumulate/hedge?

## Concepts introduced

- **Agent Engine instance (`reasoningEngine`)** — a standalone cloud resource that backs Memory Bank. Created independently of any agent deployment; no Agent Runtime required. `client.agent_engines.create()`.
- **`VertexAiMemoryBankService`** — ADK's `BaseMemoryService` implementation, imported from `google.adk.memory`. Wires into `Runner(memory_service=...)` alongside `session_service=`.
- **Scope** — key/value dict (default `{"user_id": ...}`; we used `{"app_name": ..., "user_id": ...}`) determining which memories are visible to a given request. Exact match, not hierarchical.
- **Memory topics** — gate what content Memory Bank considers worth extracting. Two kinds:
  - **Managed topics**: `USER_PERSONAL_INFO`, `USER_PREFERENCES`, `KEY_CONVERSATION_DETAILS`, `EXPLICIT_INSTRUCTIONS`. Google-defined, user-centric by design.
  - **Custom topics**: developer-defined `label` + `description`, used as the extraction prompt. Google's docs recommend few-shot examples alongside custom topics.
- **Instance-level customization** — topics, few-shot examples, consolidation depth, embedding model, generation model, and TTL are all configured via `client.agent_engines.update(config={"context_spec": {"memory_bank_config": ...}})` — not passed per-call to `generate()`.
- **`revisions_per_candidate_count`** — consolidation setting controlling how many historical revisions of a candidate memory are considered when merging new information. Default 1.
- **Consolidation** — the process by which new extracted content is merged with existing memories: per Google's docs, may ADD, UPDATE, or DELETE. This is the mechanism we adversarially tested.

## What changed or observed

1. Created one Agent Engine instance (`reasoningEngine`), region `us-central1`, matching Stage 5's existing Vertex config. No Runtime deployment.
2. Wired `VertexAiMemoryBankService` into `pipeline.py`'s `Runner` — zero behavior change confirmed via existing smoke test.
3. Confirmed Sessions and Memory Bank are genuinely separate stores — nothing auto-writes to long-term memory; requires explicit `add_session_to_memory`.
4. Confirmed default managed topics correctly extract nothing from vendor-research content (not a bug — topics are user-centric by design) and correctly extract a stated preference under `USER_PREFERENCES`.
5. Added a custom `VENDOR_FACTS` topic + one few-shot example at the instance level. Confirmed vendor-research content now extracts cleanly.
6. Ran six adversarial contradiction tests across custom and managed topics, isolated and non-isolated records, soft and sharp (discrete numeric) claims. **All six hedged.** None superseded, none duplicated.
7. Ran a fourth contradiction on the same isolated record — hedge chained rather than collapsed, preserving all four historical values in order.
8. Raised `revisions_per_candidate_count` from default (1) to 5 and re-ran the contradiction test. **No change in behavior.** Rules out revision-depth as the mechanism controlling hedge-vs-supersede.

## How to run

Requires: `AGENT_ENGINE_ID` in `.env` (created once via a setup script, not committed — see Gotchas). `google-cloud-aiplatform>=1.111.0` (tested against 1.158.0), `google-adk` 2.1.0.

```powershell
python configure_vendor_topic.py      # one-time: adds VENDOR_FACTS custom topic
python memory_split_test.py           # Step 2/3: session vs. memory split, extraction check
python memory_supersession_test.py    # Step 4: HQ contradiction (soft claim)
python memory_supersession_test2.py   # Step 4: founding year contradiction (sharp claim)
python memory_numeric_test.py         # Step 4: isolated entity + managed-topic parallel test
python memory_numeric_test2.py        # Step 4: third contradiction, same record
python configure_revision_depth.py    # sets revisions_per_candidate_count=5
python memory_numeric_test3.py        # Step 4: fourth contradiction, testing the config change
python list_memories.py               # ground-truth check, bypasses search_memory query-matching
```

## Observations

**Extraction is topic-gated, not content-gated.** A vendor-facts conversation extracts zero memories under default managed topics — correct behavior, not a defect. Extraction only activates for content matching a defined topic's description. This is a materially different configurability model from Mem0's `infer` flag: Mem0 configures extraction on/off per call; Memory Bank configures it via topic definitions at the instance level, applying to all future calls in that scope.

**Consolidation does not supersede on contradiction. It hedges, and hedges chain.** Across six adversarial tests — HQ location, founding year, a stated preference, and three sequential rounds on a fresh isolated entity — every single contradiction was absorbed into the existing record as a parenthetical or "though previously noted as" hedge. Record count never increased from a contradiction (no duplication, unlike Mem0). But the old claim was never dropped either (no true supersession, despite Google's docs stating a memory "may be deleted if the new information contradicts it" — that didn't happen in any of our six tests, none of which used `EXPLICIT_INSTRUCTIONS`/forget phrasing, which is where the docs tie that behavior).

**Hedges compound without bound.** A record contradicted three times contains all three historical values, in order, with temporal language ("earlier," "previously"). This is not a fixed one-shot hedge — it's an accreting chain. By round four, the fact read: *"2,000 employees, though previously noted as having 1,000, 500, and earlier 42 employees."*

**`revisions_per_candidate_count` is not the mechanism.** Raised from default 1 to 5, re-ran the same contradiction pattern — behavior unchanged. The setting's documented purpose (revision depth considered during consolidation) doesn't appear to control hedge-vs-supersede resolution. Working theory, not confirmed: consolidation reads the current fact **text** and asks the model to reconcile it with new input, rather than making a structured keep/replace/delete decision over discrete revision objects.

**Topic type doesn't change the behavior.** Managed topic (`USER_PREFERENCES`) and custom topic (`VENDOR_FACTS`) hedged identically. This rules out "our custom topic definition caused this" as an explanation — it's general Memory Bank consolidation behavior.

**Dashboard metrics would mask this finding.** Record count stayed flat, `update_time` advanced normally on every contradiction — both signals a monitoring dashboard would read as healthy consolidation. The degradation is only visible by reading the fact text itself.

## AAG-relevant findings (RFI dims touched)

Not applicable — per this track's separation rule, AAG framing/action items are explicitly out of scope for this document. Findings above are stated as observations only.

## Cross-platform contrast: contradiction/supersession handling

| Platform | Duplicates on contradiction? | Resolves contradiction? | Evidence tier |
|---|---|---|---|
| Mem0 OSS (9.1) | Yes — appends silently, no consolidation attempt | No | [observed] |
| AWS AgentCore (9.2) | Over-extracts generally; consolidation mechanism exists with CloudWatch logs | Not tested | [vendor-docs + happy-path observed] |
| Vertex Memory Bank (9.3) | No — merges into same record, no duplicate | No — hedges and chains rather than resolving | [observed], n=6 |

None of the three platforms tested cleanly resolves a contradiction. They fail differently: Mem0 by ignoring it (duplicate records), Memory Bank by absorbing it (one record, growing ambiguity), AgentCore unknown pending an adversarial test equivalent to what was run here.

## Gotchas

- `vertexai.types` (per current Google docs) does not exist on `google-cloud-aiplatform==1.158.0`. Real path: `vertexai._genai.types`. Confirm via `dir()` before trusting doc-shown import paths.
- Custom memory topics are configured at the **instance level** via `client.agent_engines.update()`, not passed per-`generate()` call. Any `update()` call replaces the full `customization_configs` block — must re-declare existing topics/examples or they're silently dropped.
- `search_memory`'s query-matching is unreliable for verification — it returned an unrelated preference memory as a "match" for a "Solace" query. Use `client.agent_engines.memories.list()` directly for ground truth; don't trust `search_memory` counts when testing.
- Extraction and consolidation are asynchronous; a 10-second sleep was sufficient in all tests here but isn't a documented guarantee.
- `agent_engine.api_resource.name` and console/API responses include project number and service account identity — scrub before any commit (public repo).
- Default managed topics will silently extract nothing from non-user-centric content. Don't mistake this for a broken pipeline — it's the intended behavior; a custom topic is required for domain content like vendor facts.

## Next stage

- 9.4 — Azure MAF harness + Foundry IQ (not started).
- Open, not pursued in this stage: whether `STRUCTURED_PROFILE` memory type (schema-constrained) handles contradiction differently than `NATURAL_LANGUAGE_COLLECTION` (used throughout this stage). Genuinely separate investigation, not a continuation.
- Open: AgentCore (9.2) has never been adversarially tested for supersession the way Memory Bank was here. The cross-platform table's AgentCore row remains the weakest link in the track — revisiting it with an equivalent contradiction test would close the gap.
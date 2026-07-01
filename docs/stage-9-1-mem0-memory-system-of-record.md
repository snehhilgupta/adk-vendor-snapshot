Requires `.env` inside `vendor_snapshot/` with `GOOGLE_GENAI_USE_VERTEXAI=TRUE`,
`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`; ADC via
`gcloud auth application-default login`. Qdrant data persists in
`vendor_snapshot/qdrant_data/` (gitignored).

## Observations (per-test)

**Latency — the core result.** Three-tier profile, all measured:
- Cold pipeline (miss): **118.6s** — orchestrator + 2 grounded search agents + formatter.
- Warm hit (same process): **0.1s** — cache, no pipeline, no Vertex LLM call.
- Cold hit (new process, disk load): **5.7s** — imports + Memory construction + Qdrant load.

Cache converts a ~2-minute grounded call into a 100ms lookup on repeat queries.

**Cross-session persistence: PASS.** Fresh interpreter read the on-disk Qdrant
and served Solace from cache — not in-process memoization. Level-3 system-of-record
claim demonstrated. Qdrant flushes to disk (`collection/`, `meta.json`); the
`msvcrt`/`portalocker` shutdown tracebacks are interpreter-teardown noise, not
data loss.

**Staleness gate: detection PASS, supersession FAIL.** `force_refresh=True` and
`STALENESS_DAYS=0` both correctly forced `source=pipeline`. But each refresh
appended a new record — Solace count went 1 → 2 → 3 across forced + stale
refreshes. Refresh does not retire prior versions. `cache_get` is not guaranteed
to return the newest. See finding 2.2.

**Disambiguation guard: PASS, and confirmed load-bearing.** With Solace and
Solace Health both seeded, a "Solace" vector query scored Solace 0.584 vs
Solace Health 0.580 — a 0.004 gap. Vector search cannot separate them. Both
directional `cache_get` calls returned the correct entity only because the
deterministic exact-name guard overrode the ranking. Guard limitation: it
matches the requested name against stored `vendor` metadata, not snapshot
content — it cannot detect a record whose metadata is correct but whose content
is a different company (see fabricated-vendor test).

**Fabricated vendor (Quantix Mesh AI): cold run correct.** 74.3s cold pipeline
returned the right refusal — `company_name` set, all fact fields null,
`product_summary` and `confidence_note` explicitly stating it is not a single
unified company but multiple distinct entities. The refusal cached and re-served
in 0.1s (cached refusal is desirable — avoids re-running 74s on a known-fake
vendor). Note: an earlier same-vendor observation in this session came from a
stale cached record, not a live run, and is disregarded.

**Mem0 delete: PASS.** Targeted `delete(memory_id=...)` removed a single Quantix
record while leaving the Solace pair intact.

## AAG-relevant findings (mapped to RFI sections touched)

Only dimensions actually exercised are listed. Sections 3 (security/compliance),
4 (lifecycle beyond delete), 6 (vendor posture) not tested in this stage.

**1.1 Architecture & Integration — SDK / integration surface**
- Mem0 reaches Vertex asymmetrically: extraction LLM only via a third-party
  LiteLLM shim (no native `vertex_ai` LLM provider in 2.0.8; upstream issue
  #3990 open); embeddings via native `vertexai` provider. Not single-auth.
- Native `vertexai` embedder rides the deprecated `google-cloud-aiplatform`
  SDK surface (`vertexai.language_models`), removal dated June 24 2026 — a
  durability risk.
- Mem0 + LiteLLM co-install downgraded `openai` 2.44 → 2.30 (transitive pin
  conflict, silently resolved).
- `search()` rejects top-level `user_id`; `add()` accepts it. Asymmetric
  write/read API within the same version.

**1.2 Memory abstraction & scoping**
- Mem0 is accessed as a decoupled service-layer API, not embedded in the agent
  runtime. Single `vendor_cache` scope with vendor in metadata worked; semantic
  search ranks across all vendors in one scope.
- Vector store is configurable (Qdrant default, others via config) — abstraction
  is not hard-coupled.

**1.3 Deployment / outbound dependencies**
- Full self-host on GCP achieved, zero new outbound vendor calls (no OpenAI,
  no AI Studio) once extraction routed through LiteLLM→Vertex.
- Telemetry: `telemetry: False` in config did NOT suppress PostHog — the client
  still initialized. Opt-out via config alone is unreliable in 2.0.8; env-var
  `MEM0_TELEMETRY=False` added as backstop.

**2.1 Extraction + read-after-write**
- `infer=False` stores verbatim — snapshot JSON preserved byte-for-byte, no
  extraction call fired (cheaper write: one embed, no LLM). Confirmed as the
  correct mode for a system-of-record cache.
- `infer=True` comparison: **NOT TESTED** — open item. RFI 2.1 finding is
  therefore partial (raw path only).
- Dedup observed: re-adding an identical fact returned `NOOP` (empty results),
  not a duplicate. Idempotent on identical input.

**2.2 Temporal validity / supersession**
- **No supersession in OSS `infer=False`.** Staleness detection and
  refresh-triggering work; retirement of superseded records does not. Refresh
  appends, accumulating multiple versions of differing freshness. "Latest wins"
  must be enforced by the integration layer — Mem0 does not provide it. Maps
  directly to the Platform upsell ("temporal reasoning, memory decay") printed
  by OSS itself, implying these are paid-tier gated.

**2.3 Hybrid retrieval + confidence ranking**
- Hybrid retrieval is not default-on in OSS: BM25 disabled (`fastembed` not
  installed), spaCy models absent. Vector-only out of the box; hybrid requires
  `mem0ai[extras]`/`[nlp]` — not tested.
- Vector similarity is an unreliable disambiguation/confidence signal for
  near-name entities (0.584 vs 0.580) and weak for structured-JSON storage
  (0.643 on a bare-name query against a JSON blob). The deterministic guard, not
  the score, does the disambiguation work.

**5.x Operational readiness (partial)**
- Standalone ADK invocation does not inherit the `adk web` `.env` autoload —
  Vertex backend selection requires explicit `load_dotenv()` before agent import.
  Carries forward to any deployment surface (Stage 10).
- Cache is content-blind: it stores whatever the pipeline returns (barring
  `_parse_error`) with no write-time confidence gate. A bad pipeline run — e.g.
  a hallucinated substitution — would be persisted and re-served indefinitely.
  Memory-poisoning-adjacent: a confidence gate must live in the integration
  layer, not Mem0.
- `_parse_error` results are correctly excluded from the cache (graceful
  degradation).
- Targeted delete-by-id works (lifecycle, RFI 4 — the one section-4 point touched).

## Mem0 vs Vertex AI Memory Bank (running contrast)

| Dimension | Mem0 OSS (tested) | Vertex AI Memory Bank |
|---|---|---|
| Deployment coupling | Decoupled service, self-hostable | Managed, coupled to Agent Engine — not tested |
| Extraction location | LiteLLM→Vertex (shim) or OpenAI default | Managed on Vertex — not tested |
| Vector backend | Pluggable (Qdrant default), self-owned | Managed, opaque — not tested |
| Supersession/temporal | Absent in OSS infer=False (measured) | Claimed managed feature — not tested |
| Hybrid retrieval | Opt-in extras, off by default | Not tested |
| Telemetry/outbound | PostHog on by default, opt-out unreliable | N/A managed — not tested |
| Cost model | Self-hosted infra + Vertex calls | Managed pricing — not tested |

Vertex Memory Bank not exercised in this stage. All contrast rows marked "not
tested" are architecture-inferred at most; no operational comparison claimed.

## Gotchas hit

- `text-embedding-005` via Mem0's `vertexai` embedder silently defaults to
  256-dim (Mem0 2.0.8 default is `gemini-embedding-001` @ 256). Must pin
  `embedding_dims: 768` in embedder AND `embedding_model_dims: 768` in
  vector_store — the two are independent and a mismatch throws a shape error at
  query time.
- LiteLLM reads Vertex project/location from `DEFAULT_VERTEXAI_PROJECT` /
  `DEFAULT_VERTEXAI_LOCATION`, not `GOOGLE_CLOUD_*`. Bridge the names or Vertex
  routing fails.
- `load_dotenv()` must run before `from agent import root_agent`, or the Gemini
  clients construct against the wrong backend (AI Studio) and demand an API key.
- Poisoned Qdrant collection after a dim change: delete `qdrant_data/` before
  re-running, or the old dimensionality persists.
- Windows shutdown tracebacks (`msvcrt`/`portalocker`, `sys.meta_path is None`)
  are Qdrant destructor noise on interpreter exit — not errors.

## Next stage

- Open test: `infer=True` comparison to close RFI 2.1 (inferred vs raw storage).
- Open architectural decision (documented, not fixed): supersession — refresh
  currently appends. Options are delete-before-write (true cache) or newest-wins
  at read (versioned history). Deferred.
- Stage 6 (deterministic vendor-name-match Critic) remains the correct next ADK
  step — the fabricated-vendor and content-blind-cache findings both point to it.
- Stage 10: deployment surfaces; the `.env`/Runner findings carry forward.
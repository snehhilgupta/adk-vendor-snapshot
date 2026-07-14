# Stage 9.2 — AWS AgentCore Memory (Managed)

## Evidence basis

This stage is a **guided managed-workshop build**, not a self-authored artifact. The
agent (a nutrition coach) and its code came from the [AWS AgentCore samples — memory lab](https://github.com/awslabs/agentcore-samples/tree/main/01-features/04-manage-context-of-your-agent/memory);
the findings below are my observations of that environment, not code I wrote. Evidence
tiers are marked per finding:

- **[observed]** — I ran it and read the actual output (test harness, CLI).
- **[vendor-docs]** — stated in AWS workshop/product documentation, not independently verified.
- **[architect]** — confirmed verbally by an AWS architect, not customer-verifiable.

This is a weaker evidence basis than Stage 9.1 (Mem0), which I built and stress-tested
myself. Nothing here was adversarially tested the way the fabricated-vendor case was in 9.1.

**Workload mismatch, stated up front:** the nutrition agent exercises *conversational
personalization* memory (remember a user's dietary facts across sessions). Stage 9.1
exercised *structured system-of-record caching* (vendor snapshots). These are different
memory workloads — findings do not map one-to-one, and any comparison below accounts
for that.

## Goal

Observe how AWS's managed memory service (Amazon Bedrock AgentCore Memory) handles
short-term and long-term memory, and contrast its managed model against the self-hosted
Mem0 OSS approach from Stage 9.1.

## Concepts introduced

- **AgentCore Memory** — managed agent-memory service. Two tiers: short-term (raw
  interaction events) and long-term (asynchronously extracted, structured insights).
- **Managed storage abstraction** — the backing store is not exposed to the customer
  account; you interact via the `bedrock-agentcore` API, not a database.
- **Memory strategies** — extraction modes (USER_PREFERENCE, SEMANTIC, SUMMARIZATION,
  EPISODIC) that determine what gets distilled from raw events.
- **Namespaces** — hierarchical paths (`/users/{actorId}/preferences/`) that scope and
  isolate memories; the primary multi-tenancy boundary.

## What was observed

**Managed memory resource exists; backing store does not appear in the customer account. [observed]**
`aws dynamodb list-tables` returned only the application's own domain table
(`health-tracker`, a per-user meal log keyed by `user_id` + `timestamp_type`) — not any
memory store. `aws bedrock-agentcore-control list-memories` returned an active managed
resource. So the memory backend is abstracted into AWS's service plane, not visible or
manageable from the customer side. DynamoDB is the stated short-term backing store
**[architect]**, but this is not customer-verifiable — the API returns a resource ARN,
not a table.

*Distinction worth keeping straight:* the visible `health-tracker` DynamoDB table is the
agent's **application data** (a tool-backed meal log), NOT the memory backend. "The agent
uses DynamoDB" conflates two layers — the app's domain store (visible) and the memory
service's hidden backend (not visible).

**Long-term extraction produces typed, namespaced records. [observed]**
A long-term-memory test showed 5 extracted memories across two namespaces for one actor:
- `/users/{actorId}/preferences/` — 2 records (e.g. breakfast is the favorite meal, enjoys hearty breakfasts)
- `/users/{actorId}/facts/` — 3 records (e.g. gluten allergy requiring all meals gluten-free)

The stored records are **distilled, not verbatim** — raw conversation was reshaped into
structured fact statements. This is the managed service's default extraction behavior;
the customer does not choose verbatim-vs-extracted the way Mem0 exposes `infer`.

**Cross-session personalization worked. [observed]**
In a fresh session with no restated preferences, the prompt "what should I eat for
breakfast tomorrow" returned gluten-free, high-protein recommendations — the agent
retrieved the stored facts across the session boundary. This is the managed analogue of
the 9.1 cross-session persistence result.

**Extraction over-generates redundant records. [observed] + [vendor-docs]**
The two `/preferences` records were near-duplicates, and a `/facts` record restated a
preference already held in `/preferences`. AWS documentation acknowledges this directly:
USER_PREFERENCE "may extract broad or overlapping preferences" and SEMANTIC "can produce
redundant memories if similar facts are stated repeatedly." Observation and vendor docs
agree — extraction accumulates redundancy.

## AAG-relevant findings (RFI dimensions touched)

Marked by tier. Only dimensions the workshop actually exercised or documented.

- **1.2 scoping / multi-tenancy [observed + vendor-docs]** — namespaces are the isolation
  boundary, hierarchical and tenant-aware (`/tenants/{tenantId}/users/{actorId}/`,
  shared `/org/policies/`). Richer than Mem0's single flat scope.
- **1.3 deployment / control [observed]** — storage fully abstracted; no backend access,
  no self-host, no fork. Opposite of Mem0 OSS's full-control/full-responsibility model.
- **2.1 extraction [observed]** — managed extraction on by default, not customer-controlled;
  reshapes raw input into typed facts. Contrast: Mem0 let me choose `infer=False` (verbatim).
- **3.x governance [vendor-docs]** — namespace access enforceable via IAM condition keys
  (`bedrock-agentcore:namespace`). Mem0 OSS had no comparable governance surface.
- **4.x lifecycle [vendor-docs]** — four configurable strategies, retention via `--expiry`
  (30 days in lab), tunable retrieval (`top_k`, `relevance_score`).
- **5.1 observability [vendor-docs]** — CloudWatch extraction AND consolidation logs
  (`/aws/vendedlogs/bedrock-agentcore/memory/...`). Consolidation visibility is notable —
  it's exactly what Mem0 OSS lacked, which made the 9.1 append-not-supersede defect
  invisible until I counted records manually.
- **Cross-agent sharing [vendor-docs]** — multiple agents on one `memory_id` with shared
  namespaces. Not exercised (single-agent workshop); noted as a managed capability the
  Mem0 cache didn't have.

## Mem0 OSS (9.1) vs AgentCore Memory (9.2) — the contrast that matters

Different workloads (cache vs conversational personalization), so this is architectural,
not a benchmark.

| Dimension | Mem0 OSS (9.1, self-built) | AgentCore Memory (9.2, workshop) |
|---|---|---|
| Storage | Self-hosted (Qdrant local), full control/visibility | Managed, abstracted, not customer-visible |
| Extraction | Customer choice: `infer=False` verbatim or `infer=True` | Managed default, distilled, not customer-controlled |
| Scoping | Single flat scope, vendor in metadata | Hierarchical namespaces, tenant-aware |
| Governance | None in OSS | IAM namespace condition keys [vendor-docs] |
| Consolidation visibility | None — append defect was invisible | CloudWatch consolidation logs [vendor-docs] |
| Redundant extraction | N/A (verbatim cache) | Observed + vendor-acknowledged |
| Control vs convenience | Full control, full responsibility | Low effort, low control |

**Through-line finding:** memory extraction accumulates redundancy as a general problem.
Mem0 OSS appended duplicate versions on refresh with no consolidation and no visibility
(the 9.1 supersession defect). AgentCore also over-extracts overlapping records — but
exposes consolidation logs and managed strategies to handle it. Same hard problem,
different maturity: OSS leaves consolidation to you and hides it; the managed service
does it and logs it.

## Gotchas / notes

- The visible DynamoDB table is app data, not the memory backend — easy to conflate.
- Managed abstraction means the DynamoDB-backend claim cannot be customer-verified even
  with CLI access; it stays architect-confirmed.
- Workshop environment is ephemeral — observations captured live, not re-runnable.

## Next stage

- 9.3 — Vertex AI Memory Bank (managed, Google). The managed-Google counterpart; will
  complete the managed-vs-self-hosted and cross-cloud picture.
- Open comparison thread: consolidation/supersession maturity across all four platforms
  is emerging as the sharpest cross-stage axis.
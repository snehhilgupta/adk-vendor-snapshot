"""
mem0_store.py — Mem0 OSS as system-of-record cache for vendor snapshots.

Stage 9.1. Wraps the proven Vertex-on-GCP config:
  - LLM (fact extraction): litellm -> vertex_ai/gemini-2.5-flash
  - Embedder: native vertexai text-embedding-005, 768-dim, task-typed
  - Vector store: Qdrant on-disk local (persists across sessions)

Public API:
  get_memory()                         -> singleton Memory instance
  cache_get(vendor)                    -> dict | None  (deterministic name-matched hit)
  cache_put(vendor, snapshot, infer)   -> add result
  is_stale(record)                     -> bool
"""

import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# --- env setup: load .env (lives in this package dir) -----------------------
load_dotenv()

# Disable Mem0 telemetry via env var (config flag alone did not suppress PostHog in 2.0.8).
os.environ.setdefault("MEM0_TELEMETRY", "False")

# LiteLLM reads Vertex project/location from these names, NOT GOOGLE_CLOUD_*.
# Bridge the ADK-style names so the two conventions don't collide.
if "GOOGLE_CLOUD_PROJECT" in os.environ:
    os.environ.setdefault("DEFAULT_VERTEXAI_PROJECT", os.environ["GOOGLE_CLOUD_PROJECT"])
if "GOOGLE_CLOUD_LOCATION" in os.environ:
    os.environ.setdefault("DEFAULT_VERTEXAI_LOCATION", os.environ["GOOGLE_CLOUD_LOCATION"])

from mem0 import Memory

# --- constants --------------------------------------------------------------
CACHE_USER_ID = "vendor_cache"          # single scope; vendor carried in metadata
COLLECTION_NAME = "vendor_snapshots"     # real collection (not the smoketest one)
QDRANT_PATH = "./qdrant_data"            # on-disk, relative to vendor_snapshot/
STALENESS_DAYS = 30                      # Level-3 freshness window

_CONFIG = {
    "llm": {
        "provider": "litellm",
        "config": {
            "model": "vertex_ai/gemini-2.5-flash",
            "temperature": 0.0,
            "max_tokens": 2000,
        },
    },
    "embedder": {
        "provider": "vertexai",
        "config": {
            "model": "text-embedding-005",
            "embedding_dims": 768,
            "memory_add_embedding_type": "RETRIEVAL_DOCUMENT",
            "memory_update_embedding_type": "RETRIEVAL_DOCUMENT",
            "memory_search_embedding_type": "RETRIEVAL_QUERY",
        },
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": COLLECTION_NAME,
            "path": QDRANT_PATH,
            "embedding_model_dims": 768,
            "on_disk": True,
        },
    },
    "telemetry": False,
}

# --- singleton --------------------------------------------------------------
_memory = None


def get_memory():
    """Return a process-wide singleton Memory instance."""
    global _memory
    if _memory is None:
        _memory = Memory.from_config(_CONFIG)
    return _memory


# --- helpers ----------------------------------------------------------------
def _normalize(vendor: str) -> str:
    return vendor.strip().lower()


def is_stale(record: dict) -> bool:
    """True if the record's created_at is older than STALENESS_DAYS.

    Staleness is evaluated on the stored timestamp; the wrapper decides
    whether to act on it. Returns True (treat as stale) if no timestamp.
    """
    ts = record.get("created_at")
    if not ts:
        return True
    try:
        created = datetime.fromisoformat(ts)
    except ValueError:
        return True
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - created
    return age > timedelta(days=STALENESS_DAYS)


def cache_get(vendor: str):
    """Semantic search scoped to vendor_cache, then deterministic name match.

    Returns the matching record dict (incl. created_at, metadata) or None.
    The exact-name guard prevents Solace / Solace Health cross-hits that
    pure vector ranking would allow.
    """
    m = get_memory()
    target = _normalize(vendor)
    results = m.search(
        query=vendor,
        filters={"user_id": CACHE_USER_ID},
        limit=10,
    )
    for rec in results.get("results", []):
        meta = rec.get("metadata") or {}
        if _normalize(meta.get("vendor", "")) == target:
            return rec
    return None


def cache_put(vendor: str, snapshot: dict, infer: bool = False):
    """Store a vendor snapshot.

    infer=False : store verbatim (Mem0 as dumb system-of-record cache).
    infer=True  : let Mem0's extraction LLM reshape into its memory model.

    store_mode metadata tags which path produced the record so both can
    coexist in one collection for the RFI 2.1 comparison.
    """
    m = get_memory()
    payload = json.dumps(snapshot, ensure_ascii=False)
    metadata = {
        "vendor": vendor,
        "store_mode": "inferred" if infer else "raw",
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }
    return m.add(
        payload,
        user_id=CACHE_USER_ID,
        metadata=metadata,
        infer=infer,
    )
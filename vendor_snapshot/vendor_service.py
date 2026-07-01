"""
vendor_service.py — Mem0-gated entry point for vendor snapshots.

Check-and-gate around the Stage 5 pipeline:
  - cache_get first
  - on fresh hit: return cached, skip pipeline (and skip all Vertex calls)
  - on miss / stale / forced: run pipeline, store result, return fresh

Malformed pipeline output (_parse_error) is never cached.
"""

import asyncio
from mem0_store import cache_get, cache_put, is_stale
from pipeline import run_pipeline


def get_vendor_snapshot(vendor: str, force_refresh: bool = False) -> dict:
    """Return a vendor snapshot, using Mem0 as system-of-record cache.

    Returns:
        {
          "vendor": <str>,
          "source": "cache" | "pipeline",
          "stale_refresh": <bool>,   # True if a stale hit forced a re-run
          "snapshot": <dict>,        # the VendorSnapshot, or _parse_error dict
        }
    """
    cached = cache_get(vendor)

    if cached and not force_refresh:
        stale = is_stale(cached)
        if not stale:
            import json
            return {
                "vendor": vendor,
                "source": "cache",
                "stale_refresh": False,
                "snapshot": json.loads(cached["memory"]),
            }
        # stale -> fall through to refresh, flag it
        stale_refresh = True
    else:
        stale_refresh = False

    # miss / stale / forced -> run the real pipeline
    snapshot = asyncio.run(run_pipeline(vendor))

    if snapshot.get("_parse_error"):
        # do NOT cache malformed output
        return {
            "vendor": vendor,
            "source": "pipeline",
            "stale_refresh": stale_refresh,
            "snapshot": snapshot,
        }

    cache_put(vendor, snapshot, infer=False)
    return {
        "vendor": vendor,
        "source": "pipeline",
        "stale_refresh": stale_refresh,
        "snapshot": snapshot,
    }
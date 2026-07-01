"""
pipeline.py — programmatic entry point for the Stage 5 SequentialAgent.

Wraps root_agent (vendor_orchestrator -> vendor_formatter) in an ADK Runner
so the pipeline can be invoked for a single vendor outside `adk web` and
return the VendorSnapshot as a dict. This is what the Mem0 cache layer gates.
"""
from dotenv import load_dotenv
load_dotenv()

import json
import uuid
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent import root_agent

APP_NAME = "vendor_snapshot_pipeline"
USER_ID = "pipeline_user"


async def run_pipeline(vendor: str) -> dict:
    """Run the full Stage 5 pipeline for one vendor. Returns parsed snapshot.

    On JSON parse failure, returns {"_parse_error": True, "raw": <text>}
    so the caller can decide — we do not silently swallow malformed output.
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # Fresh session per run — avoids the session-bleed quirk from adk web.
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    message = types.Content(role="user", parts=[types.Part(text=vendor)])

    final_text = None
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text

    if final_text is None:
        return {"_parse_error": True, "raw": None}

    try:
        return json.loads(final_text)
    except (json.JSONDecodeError, TypeError):
        return {"_parse_error": True, "raw": final_text}
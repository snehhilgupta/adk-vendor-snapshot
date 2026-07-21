"""
memory_split_test.py — Stage 9.3 Step 2.

Diagnostic only. Proves Sessions and Memory Bank are separate stores:
runs one vendor through the pipeline (session-only, as normal), checks
Memory Bank is empty, explicitly writes the session to memory, checks
again. Does not modify pipeline.py or run_pipeline().
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
import uuid
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import VertexAiMemoryBankService
from google.genai import types

from agent import root_agent

APP_NAME = "vendor_snapshot_pipeline"
USER_ID = "pipeline_user"


async def main():
    session_service = InMemorySessionService()
    memory_service = VertexAiMemoryBankService(
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ["GOOGLE_CLOUD_LOCATION"],
        agent_engine_id=os.environ["AGENT_ENGINE_ID"],
    )
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service,
    )

    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    print("--- Running pipeline for 'Solace' (session-only) ---")
    message = types.Content(role="user", parts=[types.Part(text="Solace")])
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=message,
    ):
        pass  # we only care about the memory split here, not the output

    print("--- Checking Memory Bank BEFORE explicit write ---")
    before = await memory_service.search_memory(
        app_name=APP_NAME, user_id=USER_ID, query="Solace",
    )
    print(f"Memories found: {len(before.memories)}")
    for m in before.memories:
        print(f"  - {m}")

    print("--- Explicitly writing session to Memory Bank ---")
    # Re-fetch session to get full event history before writing.
    full_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id,
    )
    await memory_service.add_session_to_memory(full_session)

    print("--- Checking Memory Bank AFTER explicit write ---")
    print("(Note: extraction is async on Google's side — may take a moment)")
    await asyncio.sleep(5)
    after = await memory_service.search_memory(
        app_name=APP_NAME, user_id=USER_ID, query="Solace",
    )
    print(f"Memories found: {len(after.memories)}")
    for m in after.memories:
        print(f"  - {m}")


if __name__ == "__main__":
    asyncio.run(main())
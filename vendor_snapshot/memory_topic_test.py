"""
memory_topic_test.py — Stage 9.3 Step 2 continued.

Isolates whether Memory Bank's default extraction topics
(USER_PERSONAL_INFO, USER_PREFERENCES, KEY_CONVERSATION_DETAILS,
EXPLICIT_INSTRUCTIONS) extract user-centric content when vendor-fact
content extracted nothing. Does not modify pipeline.py or agent.py.
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
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    # Deliberately user-centric statement — should hit USER_PREFERENCES
    # or EXPLICIT_INSTRUCTIONS under default topics, unlike a vendor query.
    statement = "Remember that I prefer concise vendor summaries under 100 words."

    print(f"--- Sending: {statement!r} ---")
    message = types.Content(role="user", parts=[types.Part(text=statement)])
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=message,
    ):
        pass  # response content irrelevant — only session history matters

    print("--- Writing session to Memory Bank ---")
    full_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id,
    )
    await memory_service.add_session_to_memory(full_session)

    print("--- Waiting for async extraction ---")
    await asyncio.sleep(10)

    print("--- Checking Memory Bank via direct list() ---")
    import vertexai
    client = vertexai.Client(
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ["GOOGLE_CLOUD_LOCATION"],
    )
    name = (
        f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}"
        f"/locations/{os.environ['GOOGLE_CLOUD_LOCATION']}"
        f"/reasoningEngines/{os.environ['AGENT_ENGINE_ID']}"
    )
    memories = list(client.agent_engines.memories.list(name=name))
    print(f"Total memories: {len(memories)}")
    for m in memories:
        print(f"  - {m}")


if __name__ == "__main__":
    asyncio.run(main())
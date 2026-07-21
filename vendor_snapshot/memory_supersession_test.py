"""
memory_supersession_test.py — Stage 9.3 Step 4.

Adversarial contradiction test. Injects a fact that directly contradicts
the existing Ottawa HQ memory for Solace, in the same scope, then checks
whether Memory Bank updates/deletes the old memory (supersession) or lets
a duplicate/contradictory record persist (accumulation) — same manual-
count method that caught Mem0's append-not-supersede defect in Stage 9.1.

Bypasses pipeline.py/agent.py deliberately — direct_contents_source gives
exact control over the contradiction, which a live web-search agent can't
guarantee.
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
import vertexai
from google.genai.types import Content, Part

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
AGENT_ENGINE_ID = os.environ["AGENT_ENGINE_ID"]

RESOURCE_NAME = f"projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
SCOPE = {"app_name": "vendor_snapshot_pipeline", "user_id": "pipeline_user"}

# Deliberately contradicts the stored fact: "headquartered in Ottawa, Canada."
CONTRADICTION_TEXT = "Solace is headquartered in San Francisco, California, not Canada."


def list_memories(client):
    memories = list(client.agent_engines.memories.list(name=RESOURCE_NAME))
    return memories


def print_memories(memories, label):
    print(f"--- {label}: {len(memories)} total ---")
    for m in memories:
        print(f"  fact: {m.fact}")
        print(f"  name: {m.name}")
        print(f"  updated: {m.update_time}")
        print()


async def main():
    client = vertexai.Client(project=PROJECT, location=LOCATION)

    print_memories(list_memories(client), "BEFORE contradiction")

    print(f"--- Injecting contradiction: {CONTRADICTION_TEXT!r} ---")
    client.agent_engines.memories.generate(
        name=RESOURCE_NAME,
        direct_contents_source={
            "events": [{
                "content": Content(
                    role="user",
                    parts=[Part(text=CONTRADICTION_TEXT)],
                )
            }]
        },
        scope=SCOPE,
    )

    print("--- Waiting for async extraction + consolidation ---")
    await asyncio.sleep(10)

    print_memories(list_memories(client), "AFTER contradiction")


if __name__ == "__main__":
    asyncio.run(main())
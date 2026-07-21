"""
memory_supersession_test2.py — Stage 9.3 Step 4, second contradiction.

Sharper adversarial test than the location contradiction: founding year is
a discrete, singular fact (unlike HQ, which can plausibly hedge across
multiple offices). Tests whether Memory Bank's hedge-merge behavior from
test 1 was specific to soft/ambiguous claims, or is consistent behavior.
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

# Directly contradicts the stored fact: "founded in 2001."
CONTRADICTION_TEXT = "Solace was actually founded in 1996, not 2001."


def list_memories(client):
    return list(client.agent_engines.memories.list(name=RESOURCE_NAME))


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
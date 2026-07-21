"""
memory_numeric_test3.py — Stage 9.3 Step 4, fourth contradiction round.

Tests whether revisions_per_candidate_count=5 (vs. default 1) changes
hedge-chaining behavior. Current record: "1000, though previously noted
as 500 and earlier 42." Injecting a fourth number under the new config.
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

FOURTH_CONTRADICTION_TEXT = "TestVendorAlpha has 2000 employees, not 1000."


def list_memories(client):
    return list(client.agent_engines.memories.list(name=RESOURCE_NAME))


def print_memories(memories, label):
    print(f"--- {label}: {len(memories)} total ---")
    for m in memories:
        print(f"  fact: {m.fact}")
        print(f"  name: {m.name}")
        print(f"  updated: {m.update_time}")
        print()


def generate(client, text):
    client.agent_engines.memories.generate(
        name=RESOURCE_NAME,
        direct_contents_source={
            "events": [{
                "content": Content(role="user", parts=[Part(text=text)])
            }]
        },
        scope=SCOPE,
    )


async def main():
    client = vertexai.Client(project=PROJECT, location=LOCATION)

    print_memories(list_memories(client), "BEFORE fourth contradiction")

    print(f"--- Injecting fourth contradiction: {FOURTH_CONTRADICTION_TEXT!r} ---")
    generate(client, FOURTH_CONTRADICTION_TEXT)
    await asyncio.sleep(10)
    print_memories(list_memories(client), "AFTER fourth contradiction")


if __name__ == "__main__":
    asyncio.run(main())
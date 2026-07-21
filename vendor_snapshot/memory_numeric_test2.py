"""
memory_numeric_test2.py — Stage 9.3 Step 4, third contradiction round.

Tests whether hedge-accretion compounds across multiple contradictions
on the same record, or whether it eventually collapses to a single
resolved value. Current record state: "500, though previously noted
as having 42." Injecting a third number.
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

THIRD_CONTRADICTION_TEXT = "TestVendorAlpha has 1000 employees, not 500."


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

    print_memories(list_memories(client), "BEFORE third contradiction")

    print(f"--- Injecting third contradiction: {THIRD_CONTRADICTION_TEXT!r} ---")
    generate(client, THIRD_CONTRADICTION_TEXT)
    await asyncio.sleep(10)
    print_memories(list_memories(client), "AFTER third contradiction")


if __name__ == "__main__":
    asyncio.run(main())
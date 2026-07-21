"""
memory_numeric_test.py — Stage 9.3 Step 4, isolated numeric fact test
+ parallel managed-topic contradiction test.

Two independent contradiction tests in one run:
1. TestVendorAlpha (fresh entity, custom VENDOR_FACTS topic) — isolates
   the numeric-contradiction question from Solace's already-muddied record.
2. Existing USER_PREFERENCES memory (managed topic) — tests whether
   hedge-merge behavior seen on VENDOR_FACTS is custom-topic-specific or
   general Memory Bank consolidation behavior.
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

# Track 1: custom topic, fresh entity
INITIAL_FACT_TEXT = "TestVendorAlpha has 42 employees."
CONTRADICTION_TEXT = "TestVendorAlpha has 500 employees, not 42."

# Track 2: managed topic (USER_PREFERENCES), existing record
PREFERENCE_CONTRADICTION_TEXT = (
    "Actually, remember that I prefer detailed vendor summaries "
    "over 500 words, not concise ones."
)


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

    print_memories(list_memories(client), "BEFORE any new facts")

    # --- Track 1: custom topic, fresh entity ---
    print(f"--- [Track 1] Storing initial fact: {INITIAL_FACT_TEXT!r} ---")
    generate(client, INITIAL_FACT_TEXT)
    await asyncio.sleep(10)
    print_memories(list_memories(client), "[Track 1] AFTER initial fact stored")

    print(f"--- [Track 1] Injecting contradiction: {CONTRADICTION_TEXT!r} ---")
    generate(client, CONTRADICTION_TEXT)
    await asyncio.sleep(10)
    print_memories(list_memories(client), "[Track 1] AFTER contradiction")

    # --- Track 2: managed topic, existing preference record ---
    print(f"--- [Track 2] Injecting preference contradiction: {PREFERENCE_CONTRADICTION_TEXT!r} ---")
    generate(client, PREFERENCE_CONTRADICTION_TEXT)
    await asyncio.sleep(10)
    print_memories(list_memories(client), "[Track 2] AFTER preference contradiction")


if __name__ == "__main__":
    asyncio.run(main())